# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/6 17:44
# @Author  : fubin
# @Description:
函数工具：
1. 对VisualBasic（含frm）编程语言的代码文本进行分块： code_chunk_content
"""
import re


def _parse_vb_code_text(vb_code_text: str, comment_tokens: list, max_token_len: int = 2048):
    lines = vb_code_text.splitlines()

    definitions = []
    current_definition = []

    types = ['Function', 'Sub', 'Property', 'Enum', 'Type', 'If', 'Select Case', 'Do Loop', 'While', 'For Each', 'For',
             'Begin']
    # Regular expressions to detect full function and subroutine definitions, variable declarations, and calls
    start_function_regex = re.compile(r'^(Public |Private )?Function .+', re.IGNORECASE)
    end_function_regex = re.compile(r'^End (Public |Private )?Function', re.IGNORECASE)
    start_sub_regex = re.compile(r'^(Public |Private )?Sub .+', re.IGNORECASE)
    end_sub_regex = re.compile(r'^End (Public |Private )?Sub', re.IGNORECASE)
    start_property_regex = re.compile(r'^(Public |Private )?Property .+', re.IGNORECASE)
    end_property_regex = re.compile(r'^End (Public |Private )?Property', re.IGNORECASE)
    start_enum_regex = re.compile(r'^(Public |Private )?Enum .+', re.IGNORECASE)
    end_enum_regex = re.compile(r'^End (Public |Private )?Enum', re.IGNORECASE)
    start_type_regex = re.compile(r'^(Public |Private )?Type .+', re.IGNORECASE)
    end_type_regex = re.compile(r'^End (Public |Private )?Type', re.IGNORECASE)
    start_begin_regex = re.compile(r'^Begin .+', re.IGNORECASE)
    end_begin_regex = re.compile(r'^End', re.IGNORECASE)

    # 嵌套怎么处理
    start_if_regex = re.compile(r'^If .+', re.IGNORECASE)
    end_if_regex = re.compile(r'^End If', re.IGNORECASE)
    start_select_case_regex = re.compile(r'^Select Case .+', re.IGNORECASE)
    end_select_case_regex = re.compile(r'^End Select', re.IGNORECASE)
    start_doloop_regex = re.compile(r'^Do .+', re.IGNORECASE)
    end_doloop_regex = re.compile(r'^Loop', re.IGNORECASE)
    start_while_regex = re.compile(r'^While .+', re.IGNORECASE)
    end_while_regex = re.compile(r'^End While', re.IGNORECASE)
    start_for_each_regex = re.compile(r'^For Each .+', re.IGNORECASE)
    end_for_each_regex = re.compile(r'^Next', re.IGNORECASE)
    start_for_regex = re.compile(r'^For .+', re.IGNORECASE)
    end_for_regex = re.compile(r'^(Next|Exit For)+.*', re.IGNORECASE)

    def start_type(line):
        if start_function_regex.match(line):
            return 'Function'
        elif start_sub_regex.match(line):
            return 'Sub'
        elif start_property_regex.match(line):
            return 'Property'
        elif start_enum_regex.match(line):
            return 'Enum'
        elif start_type_regex.match(line):
            return 'Type'
        elif start_if_regex.match(line):
            return 'If'
        elif start_select_case_regex.match(line):
            return 'Select Case'
        elif start_doloop_regex.match(line):
            return 'Do Loop'
        elif start_while_regex.match(line):
            return 'While'
        elif start_for_each_regex.match(line):
            return 'For Each'
        elif start_for_regex.match(line):
            return 'For'
        elif start_begin_regex.match(line):
            return 'Begin'
        return None

    def end_type(line):
        if end_function_regex.match(line):
            return 'Function'
        elif end_sub_regex.match(line):
            return 'Sub'
        elif end_property_regex.match(line):
            return 'Property'
        elif end_enum_regex.match(line):
            return 'Enum'
        elif end_type_regex.match(line):
            return 'Type'
        elif end_if_regex.match(line):
            return 'If'
        elif end_select_case_regex.match(line):
            return 'Select Case'
        elif end_doloop_regex.match(line):
            return 'Do Loop'
        elif end_while_regex.match(line):
            return 'While'
        elif end_for_each_regex.match(line):
            return 'For Each'
        elif end_for_regex.match(line):
            return 'For'
        elif end_begin_regex.match(line):
            return 'Begin'
        return None

    # 只找第一层，进栈出栈
    for line_index, line in enumerate(lines):
        if len(current_definition) > 1:
            # end: same type
            if end_type(line) == current_definition[-1]['type']:
                # 出栈
                current_definition = current_definition[:-1]
                continue
            # start: same type
            if start_type(line) == current_definition[-1]['type']:
                # 进栈
                current_definition.append({
                    'type': start_type(line),
                    'start_line_idx': line_index,
                })
        elif len(current_definition) == 1:
            # end: same type,
            if end_type(line) == current_definition[-1]['type']:
                # 元祖入库，清空栈
                definitions.append({
                    'type': current_definition[-1]['type'],
                    'start_line_idx': current_definition[-1]['start_line_idx'],
                    'end_line_idx': line_index,
                })
                current_definition = []
                continue
            # start: same type
            # 进栈
            if start_type(line) == current_definition[-1]['type']:
                current_definition.append({
                    'type': start_type(line),
                    'start_line_idx': line_index,
                })
        else:
            if start_type(line):
                current_definition.append({
                    'type': start_type(line),
                    'start_line_idx': line_index,
                })

    # 开始行 到 节点 映射关系，方便后续使用
    startline_node = {definition['start_line_idx']: definition for definition in definitions}

    new_codes = []
    line_index = 0
    while line_index < len(lines):
        line = lines[line_index]

        if line.strip() == "":
            line_index += 1
            continue

        # 代码块
        if line_index in startline_node:
            new_codes.append({
                'type': startline_node[line_index]['type'],
                'start_line_idx': line_index,
                'end_line_idx': startline_node[line_index]['end_line_idx'],
                'text': '\n'.join(lines[line_index:startline_node[line_index]['end_line_idx'] + 1]),
            })
            line_index = startline_node[line_index]['end_line_idx'] + 1
        elif line:
            # 零散块
            # 判断是否是注释开头
            if line[0] in comment_tokens:
                # 连续注释，合并到上一个注释块
                if len(new_codes) > 0 and new_codes[-1]['type'] == 'comment':
                    new_codes[-1]['end_line_idx'] = line_index
                    new_codes[-1]['text'] += '\n' + line
                # 单独注释，作为一个注释块
                else:
                    new_codes.append({
                        'type': 'comment',
                        'start_line_idx': line_index,
                        'end_line_idx': line_index,
                        'text': line
                    })
            else:
                new_codes.append({
                    'type': 'code',
                    'start_line_idx': line_index,
                    'end_line_idx': line_index,
                    'text': line
                })
        line_index += 1

    for idx, node in enumerate(new_codes):
        new_codes[idx]["token_count"] = len(new_codes[idx]["text"].split(" "))
        new_codes[idx]["block_line_margin"] = 0
        if idx > 0:
            new_codes[idx]["block_line_margin"] = node["start_line_idx"] - new_codes[idx - 1]["end_line_idx"] - 1

    new_codes[0] = __remove_copyright(new_codes[0], comment_tokens)
    new_codes = __combine_short_code(new_codes, max_token_len)
    new_codes = __combine_comment_code(new_codes, max_token_len, skip_first=True)
    # new_codes = __split_long_block(new_codes, max_token_len)

    return new_codes


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
# def __split_long_block(nodes: list, max_token_len: int):
#     node_index = 0
#     while node_index < len(nodes):
#         if nodes[node_index]["token_count"] > max_token_len:
#             # 暴力拆分
#             code_text = nodes[node_index]["text"]
#             code_chunks = SimpleMDChunker_Tool.md_chunk_content.run(
#                 tool_input={"input_text": code_text, "chunk_size": max_token_len, "chunk_overlap": 0})
#             for idx, chunk in enumerate(code_chunks):
#                 chunk['type'] = nodes[node_index]['type'] + '(block)'
#                 chunk['start_line_idx'] = nodes[node_index]['start_line_idx'] + chunk['start_line_idx']
#                 chunk['end_line_idx'] = nodes[node_index]['start_line_idx'] + chunk['end_line_idx']
#             nodes[node_index:node_index + 1] = code_chunks
#         else:
#             node_index += 1
#     return nodes


def code_chunk_content(code_text: str, language: str, comment_tokens, chunk_size: int = 2048) -> None:
    if language not in ['visualbasic']:
        raise ValueError(f"language must be in ['visualbasic'], but got {language}")
    # 调用自设计分块方法
    code_nodes = _parse_vb_code_text(code_text, comment_tokens, chunk_size)
    for idx, node in enumerate(code_nodes):
        code_nodes[idx]['chunk_splitter'] = 'visualbasic_chunker'
    return code_nodes