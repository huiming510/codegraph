# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/15 09:03
# @Author  : cuils
# @Description:
"""
import os
import sys
from pathlib import Path
from .base_converter import BaseFormatConverter


class Win32ComFormatConverter(BaseFormatConverter):
    def __init__(self, app_type, cache_dir=None):
        super().__init__(cache_dir)
        if not sys.platform.startswith('win'):
            raise Exception(f"{self.__class__.__name__} only support Windows OS.")
        self.app_type = app_type

        import win32com.client as win32  # noqa

        if self.app_type == "word":
            self.app = win32.Dispatch("Word.Application") # 打开word
        elif self.app_type == "excel":
            self.app = win32.Dispatch("Excel.Application") # 打开excel
        elif self.app_type == "powerpoint":
            self.app = win32.Dispatch("PowerPoint.Application.16")  # 打开powerpoint程序
        else:
            raise ValueError(f"Office app `{self.app_type}` is not supported. only support `word`, `excel` or `powerpoint`")

        self.app.Visible = False
        self.app.DisplayAlerts = False
        self.app.ScreenUpdating = False

    @property
    def list_input_formats(self):
        return {"doc", "xls", "ppt", "docx", "xlsx", "pptx"}

    @property
    def list_output_formats(self):
        return {"pdf", "docx", "xlsx", "pptx"}

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
            raise ValueError(f"Pandoc input format `{input_format}` is not supported. only {self.list_input_formats}")
        if output_format not in self.list_output_formats:
            raise ValueError(f"Pandoc output format `{output_format}` is not supported. only {self.list_output_formats}")

        if self.app_type == "word":
            doc = self.app.Documents.Open(
                input_filepath,
                Format=0,
                ConfirmConversions=False,
                ReadOnly=True,
                AddToRecentFiles=False
            )
            doc.SaveAs(output_filepath, 12)
            doc.Close()

        elif self.app_type == "excel":
            wb = self.app.Workbooks.Open(input_filepath)  # 打开文件
            wb.SaveAs(output_filepath, FileFormat=51)  # 51 = xlOpenXMLWorkbook
            wb.Close()

        elif self.app_type == "powerpoint":
            ppt = self.app.Presentations.Open(input_filepath)  # 打开文件
            ppt.SaveCopyAs(output_filepath, 24)
            ppt.Close()

        return output_filepath

    def quit(self):
        self.app.Quit()