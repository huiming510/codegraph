# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/28 09:48
# @Author  : cuils
# @Description:
"""
import os
import subprocess
from pathlib import Path
from subprocess import SubprocessError
from .base_converter import BaseFormatConverter


class MinerUFormatConverter(BaseFormatConverter):
    def __init__(self, engine_path=None, cache_dir=None):
        super().__init__(cache_dir)
        self.engine_path = engine_path
        self.device = "cpu"
        try:
            import torch
            if torch.cuda.is_available():
                self.device = "cuda"
            cmd = [self.engine_path or "mineru", "--version"]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        except:
            raise FileNotFoundError(f"MinerU engine not found, please install it firstly.")

    @property
    def list_input_formats(self):
        return {"pdf", "png", "jpg", "jpeg"}

    @property
    def list_output_formats(self):
        return {"markdown"}

    def convert(self, input_filepath, input_format, output_format, output_suffix):
        """输入文件地址，输出转换后的文件地址
        params:
        input_filepath: 原始文件地址
        input_format: 原始文件格式
        output_format: 目标转换格式
        output_suffix: 转换后文件后缀，格式和后缀会存在差异，docx格式和后缀完全一样，markdown后缀为md
        """
        input_filepath = Path(input_filepath)
        output_dir = os.path.join(self.cache_dir, f"{input_filepath.stem}")
        # 格式作为参数传入时，不能加.，此处额外处理一下，防止传错。例：docx 和 .docx
        input_format = input_format.lstrip(".")
        output_format = output_format.lstrip(".")
        if input_format not in self.list_input_formats:
            raise ValueError(f"MinerU input format `{input_format}` is not supported. only {self.list_input_formats}")
        if output_format not in self.list_output_formats:
            raise ValueError(f"MinerU output format `{output_format}` is not supported. only {self.list_output_formats}")

        cmd = [
            self.engine_path or "mineru",
            "-p", input_filepath,
            "-o", output_dir,
            "--source", "modelscope",
            "--device", self.device,
            "-l", "japan",
        ]

        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3600) # 超时设置长点
        output_filepaths = list(Path(output_dir).rglob("*.md"))
        if p.returncode == 0 and len(output_filepaths) > 0:
            return output_filepaths[0]
        else:
            raise SubprocessError(p.stderr.encode())




if __name__ == '__main__':
    converter = MinerUFormatConverter()