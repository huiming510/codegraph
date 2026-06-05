# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/14 09:17
# @Author  : cuils
# @Description:
"""
import os
import tempfile
import subprocess
from pathlib import Path
from subprocess import SubprocessError
from .base_converter import BaseFormatConverter


class LibreofficeFormatConverter(BaseFormatConverter):
    def __init__(self, engine_path=None, cache_dir=None):
        super().__init__(cache_dir)
        self.engine_path = engine_path
        try:
            cmd = [self.engine_path or "soffice", "--version"]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        except:
            raise FileNotFoundError(f"Libreoffice engine not found")

    @property
    def list_input_formats(self):
        return {"rtf", "doc", "xls", "ppt", "docx", "xlsx", "pptx", "emf", "wmf", "x-emf", "x-wmf"}

    @property
    def list_output_formats(self):
        return {"pdf", "docx", "xlsx", "pptx", "png", "jpg", "jpeg", "gif", "bmp"}

    def convert(self, input_filepath, input_format, output_format, output_suffix):
        """输入文件地址，输出转换后的文件地址
        params:
        input_filepath: 原始文件地址
        input_format: 原始文件格式
        output_format: 目标转换格式
        output_suffix: 转换后文件后缀，格式和后缀会存在差异，docx格式和后缀完全一样，markdown后缀为md
        """
        input_filepath = Path(input_filepath)
        output_filepath = os.path.join(self.cache_dir, f"{input_filepath.stem}.{output_suffix.lstrip('.')}")
        # 格式作为参数传入时，不能加.，此处额外处理一下，防止传错。例：docx 和 .docx
        input_format = input_format.lstrip(".")
        output_format = output_format.lstrip(".")
        if input_format not in self.list_input_formats:
            raise ValueError(f"Libreoffice input format `{input_format}` is not supported. only {self.list_input_formats}")
        if output_format not in self.list_output_formats:
            raise ValueError(f"Libreoffice output format `{output_format}` is not supported. only {self.list_output_formats}")

        cmd = [
            self.engine_path or "soffice",
            "--headless",
            "--norestore",
            "--nofirststartwizard",
            "--convert-to", output_format,
            "--outdir", self.cache_dir,
            '-env:UserInstallation=file:///' + tempfile.mkdtemp(prefix='lo_').replace('\\', '/'), # 每个子进程，都有一个单独的profile，防止死锁
            input_filepath
        ]

        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)

        if p.returncode == 0 and os.path.exists(output_filepath):
            return output_filepath
        else:
            raise SubprocessError(p.stderr)




if __name__ == '__main__':
    converter = LibreofficeFormatConverter()
