# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/28 10:35
# @Author  : fubin dingsh
# @Description:
"""
import re


def remove_comments(txt: str, language: str) -> str:
    """去掉注释: 支持 C/C++, C#, Visual Basic, DEF, FRM, XML 等"""
    # 'cpp', 'c', 'visualbasic', 'csharp', 'def', 'frm', 'xml'

    # C/C++/C# 注释格式相同: 经过测试
    if language in ['c', 'cpp']:
        # 1. 多行注释 /* */
        txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.DOTALL)
        # 2. 单行注释 //
        txt = re.sub(r'(?<![\'\"])//.*$', '', txt, flags=re.MULTILINE)
    # visual basic 注释格式: 经过测试
    elif language in ['visualbasic']:
        txt = re.sub(r'(?<![\"])\'.*$', '', txt, flags=re.MULTILINE)
    # C# 注释格式: 经过测试
    elif language in ['csharp']:
        # 1. 多行注释 /* */
        txt = re.sub(r'/\*.*?\*/', '', txt, flags=re.DOTALL)
        # 2. 单行注释 //
        txt = re.sub(r'(?<![\'\"])//.*$', '', txt, flags=re.MULTILINE)
        # 3. 去掉特色注释 ///
        txt = re.sub(r'(?<![\'\"])///.*$', '', txt, flags=re.MULTILINE)
    # C/C++ 模块导出定义文件 DEF 注释格式: 经过测试
    elif language in ['def']:
        # 1. 行尾分号  ; ...
        txt = re.sub(r';.*$', '', txt, flags=re.MULTILINE)
        # 2. 行尾 // ...
        txt = re.sub(r'//.*$', '', txt, flags=re.MULTILINE)
    # .frm VB6 窗体文件，单引号行注释，前面不在双引号内（粗略）: 经过测试
    elif language in ['frm']:
        txt = re.sub(r'(?<![\"])\'' r'.*$', '', txt, flags=re.MULTILINE)
    # .vcproj	Visual C++ Project (2003-2008)	MSBuild 格式的工程描述文件（XML）: 经过测试
    elif language in ['xml']:
        # xml 注释格式
        txt = re.sub(r'<!--.*?-->', '', txt, flags=re.MULTILINE)
    # .ini 配置文件注释格式: 经过测试
    elif language in ['ini']:
        # ini 注释格式
        txt = re.sub(r'[;#].*$', '', txt, flags=re.MULTILINE)
    return txt


def remove_special_chars(txt: str) -> str:
    """去掉 emoji、特殊转义字符"""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002500-\U00002BEF"  # chinese char
        "\U00002702-\U000027B0"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"  # dingbats
        "\u3030"
        "]+", flags=re.UNICODE)
    txt = emoji_pattern.sub('', txt)
    # 2. 清特殊转义字符
    txt = re.sub(r'\\[!"#$%&\'()*+,\-./:;<=>?@[\\\]^_`{|}~]', ' ', txt)
    # 移除其他可能的乱码符号
    txt = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', ' ', txt)
    # 3. 移除零宽空格和其他不可见字符
    txt = re.sub(r'[\u200B-\u200D\uFEFF]', ' ', txt)
    # 4. 连续只有空格的空行
    txt = re.sub(r'\n\s*\n', '\n\n', txt)
    # 5. 多余空行
    txt = re.sub(r'\n{3,}', '\n\n', txt)

    return txt.strip()
