# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/4 09:14
# @Author  : cuils
# @Description:
"""
import uuid
from typing import List
from pathlib import Path
from .base_parser import BaseParser
from ..base import LinkDocument


class TXTParser(BaseParser):
    def __init__(self, logger):
        super().__init__(logger)

    @property
    def support_file_formats(self) -> List[str]:
        return ["txt", "ini", "json", "conf", "yaml", "yml"]

    def parse(self, filepath: str | Path, doc_id=None) -> List[LinkDocument]:
        # 解析XML文件
        filepath = Path(filepath).absolute()
        suffix = filepath.suffix.lstrip(".").lower()
        if suffix not in self.support_file_formats:
            raise ValueError(f"XML Parser only supports {self.support_file_formats}, but got {suffix}")

        with open(filepath, encoding="utf-8") as f:
            markdown = f.read()

        document = LinkDocument(
            doc_id=doc_id or str(uuid.uuid4()),
            content=markdown,
            metadata={"file_name": filepath.name}
        )
        return [document]