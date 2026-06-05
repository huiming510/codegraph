#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/26 13:43
# @Author  : dingsh
# @Description:
Tree-sitter代码元素抽取模块
使用tree-sitter从代码中提取类和方法信息
"""
import importlib
from pathlib import Path


# 动态导入tree-sitter语言模块
def safe_import(module_name):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def safe_read_file(file_path, encodings=None):
    """安全地读取文件，尝试多种编码"""
    if encodings is None:
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin1']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {str(e)}")
            return None
    print(f"无法使用任何编码读取文件: {file_path}")
    return None

# 导入支持的语言模块
tree_sitter_java = safe_import('tree_sitter_java')
tree_sitter_python = safe_import('tree_sitter_python')
tree_sitter_javascript = safe_import('tree_sitter_javascript')
tree_sitter_cpp = safe_import('tree_sitter_cpp')
tree_sitter_c = safe_import('tree_sitter_c')
tree_sitter_rust = safe_import('tree_sitter_rust')
tree_sitter_go = safe_import('tree_sitter_go')

try:
    from tree_sitter import Language, Parser
except ImportError:
    Language = None
    Parser = None

# 初始化支持的语言映射
def init_lang_map():
    lang_map = {}
    if tree_sitter_java and Language:
        try:
            lang_map['.java'] = Language(tree_sitter_java.language())
        except:
            pass
    if tree_sitter_python and Language:
        try:
            lang_map['.py'] = Language(tree_sitter_python.language())
        except:
            pass
    if tree_sitter_javascript and Language:
        try:
            lang_map['.js'] = Language(tree_sitter_javascript.language())
        except:
            pass
    if tree_sitter_cpp and Language:
        try:
            lang_map['.cpp'] = Language(tree_sitter_cpp.language())
            lang_map['.cc'] = Language(tree_sitter_cpp.language())
            lang_map['.cxx'] = Language(tree_sitter_cpp.language())
        except:
            pass
    if tree_sitter_c and Language:
        try:
            lang_map['.c'] = Language(tree_sitter_c.language())
        except:
            pass
    if tree_sitter_rust and Language:
        try:
            lang_map['.rs'] = Language(tree_sitter_rust.language())
        except:
            pass
    if tree_sitter_go and Language:
        try:
            lang_map['.go'] = Language(tree_sitter_go.language())
        except:
            pass
    return lang_map

LANGUAGE_MAP = init_lang_map()

# 不同语言的类和方法标识符
LANGUAGE_IDENTIFIERS = {
    '.java': {
        'class_types': ['class_declaration'],
        'method_types': ['method_declaration']
    },
    '.py': {
        'class_types': ['class_definition'],
        'method_types': ['function_definition']
    },
    '.js': {
        'class_types': ['class_declaration'],
        'method_types': ['method_definition', 'function_declaration']
    },
    '.cpp': {
        'class_types': ['class_specifier'],
        'method_types': ['function_definition']
    },
    '.c': {
        'class_types': [],
        'method_types': ['function_definition']
    },
    '.rs': {
        'class_types': ['struct_item', 'enum_item'],
        'method_types': ['function_item', 'impl_item']
    },
    '.go': {
        'class_types': ['type_spec'],
        'method_types': ['function_declaration']
    },
}

# 不同语言的命名标识符
LANGUAGE_NAME_IDENTIFIERS = {
    '.java': 'identifier',
    '.py': 'identifier',
    '.js': 'property_identifier',
    '.cpp': 'identifier',
    '.c': 'identifier',
    '.rs': 'identifier',
    '.go': 'identifier',
}

def get_parser(file_path):
    """根据文件扩展名获取相应的解析器"""
    ext = Path(file_path).suffix
    
    if ext in LANGUAGE_MAP and Parser:
        parser = Parser()
        parser.language = LANGUAGE_MAP[ext]
        return parser, ext
    
    return None, None


def extract_elements(file_path) -> list[dict]:
    """使用tree-sitter从文件中提取类和方法信息"""
    classes = []
    methods = []
    
    try:
        # 安全地读取文件内容
        code = safe_read_file(file_path)
        if code is None:
            return classes, methods
        
        # 获取对应语言的解析器
        parser, lang_ext = get_parser(file_path)
        if not parser:
            print(f"不支持的语言类型: {file_path}")
            return classes, methods
        
        tree = parser.parse(bytes(code, "utf8"))
        root_node = tree.root_node
        
        # 获取该语言的标识符
        lang_identifiers = LANGUAGE_IDENTIFIERS.get(lang_ext, {'class_types': [], 'method_types': []}) if lang_ext else {'class_types': [], 'method_types': []}
        name_identifier = LANGUAGE_NAME_IDENTIFIERS.get(lang_ext, 'identifier') if lang_ext else 'identifier'
        
        # 遍历语法树节点
        def traverse(node):
            if not node:
                return
            
            # 提取类信息
            if node.type in lang_identifiers['class_types']:
                class_info = {
                    "name": None,
                    "content": node.text.decode("utf8"),
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1
                }
                
                # 获取类名
                def find_name(node):
                    for child in node.children:
                        # 对于Java类，我们需要找到class关键字后的标识符
                        if node.type == 'class_declaration' and child.type == 'class_body':
                            # 找到class关键字前的标识符
                            for sibling in node.children:
                                if sibling.type == name_identifier and sibling.prev_sibling and sibling.prev_sibling.type == 'class':
                                    return sibling.text.decode("utf8")
                        elif child.type == name_identifier:
                            # 避免返回注解中的标识符
                            if not (child.prev_sibling and child.prev_sibling.type in ['@', 'interface', 'enum']):
                                return child.text.decode("utf8")
                        # 对于某些语言可能需要深入查找
                        result = find_name(child)
                        if result:
                            return result
                    return None
                
                class_info["name"] = find_name(node) or "anonymous"
                classes.append(class_info)
            
            # 提取方法信息
            if node.type in lang_identifiers['method_types']:
                method_info = {
                    "name": None,
                    "content": node.text.decode("utf8"),
                    "start_line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1
                }
                
                # 获取方法名
                def find_method_name(node):
                    # 对于Java方法声明，直接查找方法名
                    if node.type == 'method_declaration':
                        for child in node.children:
                            # 方法名通常在返回类型和参数列表之间
                            if child.type == name_identifier:
                                # 检查前面是否有'@'符号，避免注解名
                                is_annotation = False
                                temp = child.prev_sibling
                                while temp:
                                    if temp.type == '@':
                                        is_annotation = True
                                        break
                                    temp = temp.prev_sibling
                                
                                if not is_annotation:
                                    return child.text.decode("utf8")
                    
                    # 其他情况的通用查找
                    for child in node.children:
                        # 避免返回注解中的标识符
                        if child.type == name_identifier and not (child.prev_sibling and child.prev_sibling.type == '@'):
                            # 对于Java方法，确保我们获取的是方法名而不是注解名
                            is_annotation = False
                            temp = child.prev_sibling
                            while temp:
                                if temp.type == '@':
                                    is_annotation = True
                                    break
                                temp = temp.prev_sibling
                            
                            if not is_annotation:
                                return child.text.decode("utf8")
                        # 特殊处理JavaScript的方法定义
                        if child.type == 'identifier' and child.text.decode("utf8") == 'function':
                            continue
                        if child.type == 'property_identifier':
                            return child.text.decode("utf8")
                        # 深入查找
                        result = find_method_name(child)
                        if result:
                            return result
                    return None
                
                method_info["name"] = find_method_name(node) or "anonymous"
                methods.append(method_info)
            
            # 递归遍历子节点
            for child in node.children:
                traverse(child)
        
        traverse(root_node)
        
        return classes, methods
    
    except Exception as e:
        print(f"使用tree-sitter处理文件 {file_path} 时出错: {str(e)}")
        return classes, methods


def extract(file_path) -> list[dict]:
    """
    使用tree-sitter从文件中提取类和方法信息
    """
    return extract_elements(file_path)