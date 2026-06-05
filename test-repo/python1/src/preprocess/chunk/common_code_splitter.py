# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/26 13:43
# @Author  : fubin
# @Description:
函数工具：
1. 对常用编程语言（cpp/c/csharp/python/java）的代码文本进行语义结构分块： code_chunk_content


# 分块原理
1. 按照构建语法树: _parse_common_code_text
2. 按照语法树最外层切分（函数/类/结构体/枚举/接口/注释/字符串/数字/运算符/分隔符/关键字）: _parse_common_code_text
3. 合并相邻的注释（不超过max_token_len），合并注释节点在代码那行: _parse_common_code_text
4. 去掉首个节点为注释中可能存在copyright内容: __remove_copyright
5. 合并相邻短代码（不超过max_token_len）：__combine_short_code
6. 合并注释在前代码在后的相邻节点（不超过max_token_len）：__combine_comment_code
7. 按照chunk_size切分过长代码块（不超过max_token_len）：__split_long_block


环境：
pip install tree_sitter==0.25.2
pip install tree-sitter-c==0.24.1
pip install tree-sitter-cpp==0.23.4
pip install tree_sitter_c_sharp-0.23.1
pip install tree-sitter-python-0.25.0
pip install tree_sitter_java==0.23.5
"""

from tree_sitter import Language, Parser


SUPPORT_CODE_LANGUAGES_COMMENT_TOKENS = {
    "cpp": ["//", "/*", "*/"],
    "c": ["//", "/*", "*/"],
    "csharp": ["//", "/*", "*/", '///'],
    "python": ["#", '"""', "'''"],
    "java": ["//", "/*", "*/"],
}


def _parse_common_code_text(code_text: str, language: str, max_token_len: int = 2048):
    # 1. 加载语言
    if language.lower() == "cpp":
        import tree_sitter_cpp
        parser = Parser(Language(tree_sitter_cpp.language()))
        comment_tokens = SUPPORT_CODE_LANGUAGES_COMMENT_TOKENS["cpp"]
    elif language.lower() == "c":
        import tree_sitter_c
        parser = Parser(Language(tree_sitter_c.language()))
        comment_tokens = SUPPORT_CODE_LANGUAGES_COMMENT_TOKENS["c"]
    elif language.lower() == "csharp":
        import tree_sitter_c_sharp
        parser = Parser(Language(tree_sitter_c_sharp.language()))
        comment_tokens = SUPPORT_CODE_LANGUAGES_COMMENT_TOKENS["csharp"]
    elif language.lower() == "python":
        import tree_sitter_python
        parser = Parser(Language(tree_sitter_python.language()))
        comment_tokens = SUPPORT_CODE_LANGUAGES_COMMENT_TOKENS["python"]
    elif language.lower() == "java":
        import tree_sitter_java
        parser = Parser(Language(tree_sitter_java.language()))
        comment_tokens = SUPPORT_CODE_LANGUAGES_COMMENT_TOKENS["java"]

    else:
        raise ValueError(f"Currently only support [ CPP, C, C#, Python, Java ] these five code languages!")

    tree = parser.parse(code_text.encode())
    outer_children = tree.root_node.children

    nodes = []
    for node in outer_children:
        if node.text.decode().strip() == "":
            continue

        item = {
            "type": node.type,
            # 起始行号（从0开始）
            "start_line_idx": node.start_point.row,
            # 结束行号（从0开始）
            "end_line_idx": node.end_point.row,
            "text": node.text.decode(),
        }
        item["token_count"] = len(item["text"].split(" "))

        # 注释节点在代码那行
        if item["type"] == "comment" and len(nodes) and item['start_line_idx'] <= nodes[-1]['end_line_idx']:
            # 要换行
            nodes[-1]["text"] += "\n" + item["text"]
            # 更新结束行号
            nodes[-1]["end_line_idx"] = max(item["end_line_idx"], nodes[-1]["end_line_idx"])
            nodes[-1]["token_count"] += item["token_count"]
            continue

        # 合并相邻注释节点
        if item["type"] == "comment" and len(nodes) and nodes[-1][
            "type"] == "comment":  # and item['start_line_idx'] == nodes[-1]['end_line_idx'] + 1
            # 要换行
            nodes[-1]["text"] += "\n" + item["text"]
            # 更新结束行号
            nodes[-1]["end_line_idx"] = max(item["end_line_idx"], nodes[-1]["end_line_idx"])
            nodes[-1]["token_count"] += item["token_count"]
            continue
        nodes.append(item)

    nodes[0] = __remove_copyright(nodes[0], comment_tokens)
    nodes = __combine_short_code(nodes, max_token_len)
    nodes = __combine_comment_code(nodes, max_token_len, skip_first=True)
    # nodes = __split_long_block(nodes, language, max_token_len)

    # 计算每个代码块之间的行间距
    nodes[0]['block_line_margin'] = 0
    for idx in range(1, len(nodes)):
        nodes[idx]['block_line_margin'] = max(nodes[idx]['start_line_idx'] - nodes[idx - 1]['end_line_idx'] - 1, 0)

    return nodes


# 去掉copyright
# copyright 开始连续几行去掉
def __remove_copyright(node: dict, comment_tokens: list):
    comment_tokens = list(set(''.join(comment_tokens))) + ['/']
    if node["type"] == "comment" and 'copyright' in node['text'].lower():
        # print(node['text'], comment_tokens)
        lines = node['text'].split('\n')
        copyright_start_line_index, copyright_end_line_index = -1, -1
        for line_index, line in enumerate(lines):
            if 'copyright' in line.lower():
                copyright_start_line_index = line_index
            else:
                if line.strip() == '' or all([token in comment_tokens for token in list(line.strip())]) \
                        and copyright_start_line_index > -1 and copyright_end_line_index == -1:
                    copyright_end_line_index = line_index
        # print(copyright_start_line_index, copyright_end_line_index)
        if copyright_end_line_index > copyright_start_line_index:
            node['text'] = '\n'.join(lines[:copyright_start_line_index] + lines[copyright_end_line_index + 1:])
        else:
            raise ValueError("copyright_start_line_index must be less than copyright_end_line_index!")
    return node


# 合并类似短代码
def __combine_short_code(nodes: list, max_token_len: int):
    node_index = 1
    while node_index < len(nodes):
        # 相同类型 且 二者token和小于max_token_len
        # nodes[node_index - 1]["type"] == nodes[node_index]["type"]

        # 双方都不能为comment和fun 且 二者token和小于max_token_len
        # 'comment' not in nodes[node_index - 1]["type"] and 'comment' not in nodes[node_index]["type"]
        # 'function_definition' not in nodes[node_index - 1]["type"] and 'function_definition' not in nodes[node_index]["type"]

        if 'comment' not in nodes[node_index - 1]["type"] and 'comment' not in nodes[node_index]["type"] and \
                'func' not in nodes[node_index - 1]["type"] and 'func' not in nodes[node_index]["type"] and \
                nodes[node_index - 1]["token_count"] + nodes[node_index]["token_count"] < max_token_len:
            # 合并
            nodes[node_index - 1]["text"] += '\n' + nodes[node_index]["text"]
            nodes[node_index - 1]["end_line_idx"] = nodes[node_index]["end_line_idx"]
            nodes[node_index - 1]["token_count"] += nodes[node_index]["token_count"]
            # 删除当前节点
            nodes.pop(node_index)
        else:
            node_index += 1
    return nodes


# 合并注释到代码
def __combine_comment_code(nodes: list, max_token_len: int, skip_first: bool = True):
    node_index = 1 if not skip_first else 2
    while node_index < len(nodes):
        if nodes[node_index - 1]["type"] == "comment" and nodes[node_index]["type"] != "comment" and \
                nodes[node_index - 1]["token_count"] + nodes[node_index]["token_count"] < max_token_len:
            # 合并
            nodes[node_index - 1]['type'] = 'comment_code'
            nodes[node_index - 1]["text"] += '\n' + nodes[node_index]["text"]
            nodes[node_index - 1]["end_line_idx"] = nodes[node_index]["end_line_idx"]
            nodes[node_index - 1]["token_count"] += nodes[node_index]["token_count"]
            # 删除当前节点
            nodes.pop(node_index)
        else:
            node_index += 1

    return nodes


# 长代码块递归拆分
# def __split_long_block(nodes: list, language: str, max_token_len: int):
#     node_index = 0
#     while node_index < len(nodes):
#         if nodes[node_index]["token_count"] > max_token_len:
#             # 暴力拆分
#             code_text = nodes[node_index]["text"]
#             code_chunks = SimpleCodeChunker_Tool.code_chunk_content.run(
#                 tool_input={"input_code": code_text, "language": language, "chunk_size": max_token_len,
#                             "chunk_overlap": 0})
#             for idx, chunk in enumerate(code_chunks):
#                 chunk['type'] = nodes[node_index]['type'] + '(block)'
#                 chunk['start_line_idx'] = nodes[node_index]['start_line_idx'] + chunk['start_line_idx']
#                 chunk['end_line_idx'] = nodes[node_index]['start_line_idx'] + chunk['end_line_idx']
#             nodes[node_index:node_index + 1] = code_chunks
#         else:
#             node_index += 1
#     return nodes


def code_chunk_content(code_text: str, language: str, chunk_size: int = 2048) -> None:
    language = language.lower()
    if language not in SUPPORT_CODE_LANGUAGES_COMMENT_TOKENS:
        raise ValueError(
            f"code language {language} not in supported languages: {SUPPORT_CODE_LANGUAGES_COMMENT_TOKENS.keys()}")

    # 调用自设计分块方法
    code_nodes = _parse_common_code_text(code_text, language, max_token_len=chunk_size)
    for idx, node in enumerate(code_nodes):
        code_nodes[idx]['chunk_splitter'] = f'common_code_chunker({language})'

    return code_nodes