# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/6 17:44
# @Author  : fubin
# @Description:
函数工具：
1. 对xml（含vcproj）编程语言的代码文本进行分块： code_chunk_content
2. 对xml（含vcproj）编程语言的代码文件进行分块： code_chunk_file
3. 对xml（含vcproj）编程语言的代码目录进行分块： code_chunk_dir

环境：
pip install tree_sitter==0.25.2
pip install tree-sitter-xml==0.7.0
"""

import re
import tree_sitter_xml
from tree_sitter import Language, Parser

XML_PARSER = Parser(Language(tree_sitter_xml.language_xml()))


def _parse_xml_code_text(code_text: str, language: str, max_token_len: int = 2048):
    # 1. 加载语言
    if language.lower() != "xml":
        raise ValueError(f"目前仅支持[ XML ]这一种代码语言")

    # 想获得完整版树结构可以设置其为空[]
    # SKIP_TYPES = ["prolog", "STag", "ETag"]
    SKIP_TYPES = ["prolog", "ETag"]

    tree = XML_PARSER.parse(code_text.encode())
    nodes = [child for child in tree.root_node.children
             if not (child.type in SKIP_TYPES or child.text.decode().strip() == "")]

    node_index = 0
    while node_index < len(nodes):
        node = nodes[node_index]
        node_text = node.text.decode().strip()

        # 想获得完整版树结构可以注释掉这段代码
        # 空节点直接跳过
        if node_text == "" or (re.match(r"^<([^>]+)>[\s\S]*?</\1>$", node_text) and node_text[node_text.index(
                ">") + 1: node_text.rindex("</")].strip() == ''):
            nodes.pop(node_index)
            continue

        # 过长节点需要继续进行拆分
        node_token_count = len(node_text.split(" "))
        if node_token_count > max_token_len and node.type in ["element", 'content']:
            sub_nodes = [child for child in node.children
                         if not (child.type in SKIP_TYPES or child.text.decode().strip() == "")]
            if len(sub_nodes) > 0:
                nodes[node_index: node_index + 1] = sub_nodes
                continue

        node_index += 1

    new_nodes = [
        {
            "type": node.type,
            # 起始行号（从0开始）
            "start_line_idx": node.start_point.row,
            # 结束行号（从0开始）
            "end_line_idx": node.end_point.row,
            "text": node.text.decode(),
        } for node in nodes
        if not (node.type in SKIP_TYPES or node.text.decode().strip() == "")
    ]

    for idx, node in enumerate(new_nodes):
        new_nodes[idx]["token_count"] = len(new_nodes[idx]["text"].split(" "))
        new_nodes[idx]["block_line_margin"] = 0
        if idx > 0:
            new_nodes[idx]["block_line_margin"] = node["start_line_idx"] - new_nodes[idx - 1]["end_line_idx"] - 1

    return new_nodes


def code_chunk_content(code_text: str, language: str, comment_tokens, chunk_size: int = 2048) -> None:
    if language not in ['xml']:
        raise ValueError(f"language must be in ['xml'], but got {language}")
    # 调用自设计分块方法
    code_nodes = _parse_xml_code_text(code_text, language, chunk_size)
    for idx, node in enumerate(code_nodes):
        code_nodes[idx]['chunk_splitter'] = 'xml_chunker'

    return code_nodes
