# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/28 10:29
# @Author  : fubin
# @Description:
"""
import re
import html


def html_table_to_md(text: str) -> str:
    """把 markdown文本中可能存在 HTML 表格转成 Markdown 表格,（保留表格全部内容，包括表头），返回转换后的 Markdown 文本"""
    # 1. 提取所有 HTML 表格
    html_tables = re.findall(r"<table.*?</table>", text, re.DOTALL)
    # 2. 遍历所有 HTML 表格，转换为 Markdown 表格
    for html_table in html_tables:
        # 2.1 提取表头
        headers = re.findall(r"<th.*?</th>", html_table, re.DOTALL)
        headers = [html.unescape(re.sub(r"<.*?>", "", header.strip())) for header in headers]
        # 2.2 提取表格内容
        rows = re.findall(r"<tr.*?</tr>", html_table, re.DOTALL)
        matrix = []
        for row in rows:
            cells = re.findall(r"<td.*?</td>", row, re.DOTALL)
            cells = [html.unescape(re.sub(r"<.*?>", "", cell.strip())) for cell in cells]
            matrix.append(cells)
        # 2.3 生成 Markdown 表格
        md_rows = []
        # 5. 生成 Markdown 之前，把 None 换成 ""
        matrix = [[cell or "" for cell in row] for row in matrix]
        # 6. 生成 Markdown 表格
        if headers:
            md_rows.append("| " + " | ".join(headers) + " |")
            md_rows.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for r in matrix:
            # 6.1 过滤空行
            if not any(r.strip() for r in r):
                continue
            if md_rows:
                md_rows.append("| " + " | ".join(r) + " |")
            else:
                # 表头
                md_rows.append("| " + " | ".join(r) + " |")
                md_rows.append("| " + " | ".join(["---"] * len(r)) + " |")
        # 7. 用换行符连接所有行，形成完整的 Markdown 表格
        md_table = "\n".join(md_rows)
        # 8. 用 Markdown 表格替换原始 HTML 表格
        text = text.replace(html_table, md_table)
    return text


def remove_special_chars(txt: str) -> str:
    """删除 emoji、特殊转义字符，保留缩进"""
    # txt = "\n".join([line.strip() for line in txt.splitlines()])
    # 1. 清 emoji
    txt = re.sub(r"[\U00010000-\U0010ffff]", "", txt)
    # 2. 清特殊转义字符
    txt = re.sub(r'\\[!"#$%&\'()*+,\-./:;<=>?@[\\\]^_`{|}~]', " ", txt)
    # # 3. 连续空格压缩
    # txt = re.sub(r"[ \t]{3,}", "  ", txt)
    # 3. 连续只有空格的空行
    txt = re.sub(r"\n\s*\n", "\n\n", txt)
    # 4. 多余空行
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    return txt.strip()