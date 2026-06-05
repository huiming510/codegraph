# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/28 11:13
# @Author  : fubin
# @Description:
编码转换:对文本文件进行编码识别并转换为UTF-8输出
"""
import os
import chardet
from pathlib import Path


def transform_encoding_type(
    input_filepath: str,
    output_filepath: str,
    default_input_encode: str = "shift_jis",
    override: bool = False
) -> None:
    if not os.path.exists(input_filepath):
        raise f"File {input_filepath} does not exist!"
    if os.path.exists(output_filepath) and not override:
        raise f"File {output_filepath} already exists, and override == {override}!"

    try:
        raw = Path(input_filepath).read_bytes()
        encoding_type = chardet.detect(raw)["encoding"]
        with open(output_filepath, "w", encoding="utf8") as fout, open(input_filepath, encoding=encoding_type) as fin:
            fout.write(fin.read())

    except Exception as e:
        print(f"Error: {input_filepath} 编码转换失败 - {repr(e)}")
        with (open(output_filepath, "w", encoding="utf8") as fout,
              open(input_filepath, encoding=default_input_encode, errors="ignore") as fin):
            fout.write(fin.read())
