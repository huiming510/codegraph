# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/6 17:44
# @Author  : fubin
# @Description:
函数工具：
1. 对def编程语言的代码文本进行分块： code_chunk_content
"""

def _parse_def_code_text(def_code_text: str, comment_tokens: list, max_token_len: int = 2048):
    lines = def_code_text.splitlines()

    new_codes = []
    for line_index, line in enumerate(lines):
        if line.strip() == "":
            continue

        # 代码块
        # 注释在前，代码在后

        #  注释行
        if line[0] in comment_tokens:
            if len(new_codes) > 0 and new_codes[-1]["type"] == "comment":
                # 合并注释行
                new_codes[-1]["text"] += "\n" + line
                # 更新结束行号
                new_codes[-1]["end_line_idx"] = line_index
            else:
                new_codes.append({
                    "type": "comment",
                    "start_line_idx": line_index,
                    "end_line_idx": line_index,
                    "text": line
                })
        else:
            # 代码行
            if len(new_codes) > 0 and new_codes[-1]["type"] == "code":
                # 合并代码行
                new_codes[-1]["text"] += "\n" + line
                new_codes[-1]["end_line_idx"] = line_index
            else:
                new_codes.append({
                    "type": "code",
                    "start_line_idx": line_index,
                    "end_line_idx": line_index,
                    "text": line
                })

    for idx, node in enumerate(new_codes):
        new_codes[idx]["token_count"] = len(new_codes[idx]["text"].split("\n"))
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


# # 长代码块递归拆分
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
    if language not in ['def']:
        raise ValueError(f"language must be in ['def'], but got {language}")
    # 调用自设计分块方法
    code_nodes = _parse_def_code_text(code_text, comment_tokens, chunk_size)
    for idx, node in enumerate(code_nodes):
        code_nodes[idx]['chunk_splitter'] = 'def_chunker'
    return code_nodes