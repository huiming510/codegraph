# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/9 14:41
# @Author  : cuils
# @Description:
local 实现 pdf转markdown
todo：server实现，pdf转markdown
风险点：MinerU安装难、转换耗时长
"""
import uuid
from typing import List
from pathlib import Path
from ..base import LinkDocument
from .base_parser import BaseParser
from ..format_convert import BaseFormatConverter, MinerUFormatConverter


class PDFParser(BaseParser):
    def __init__(self, logger, converter: BaseFormatConverter=None):
        super().__init__(logger)
        self.converter = converter
        if self.converter is None:
            self.converter = MinerUFormatConverter()

    @property
    def support_file_formats(self) -> List[str]:
        return ["pdf"]

    def parse(self, filepath: str | Path, doc_id=None) -> List[LinkDocument]:
        filepath = Path(filepath).absolute()
        origin_filepath = filepath
        suffix = filepath.suffix.lstrip(".")
        if suffix not in self.support_file_formats:
            raise ValueError(f"PDF Parser only supports {self.support_file_formats}, but got {suffix}")

        try:
            md_file = self.converter.convert(
                input_filepath=filepath,
                input_format="pdf",
                output_format="markdown",
                output_suffix="md"
            )
            filepath = Path(md_file).absolute()
        except Exception as e:
            self.logger.info(f"[ConvertError]: `pdf`->`markdown` 转换失败。`{filepath}` - {repr(e)}")
            return []

        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        link_document = LinkDocument(
            doc_id=doc_id or str(uuid.uuid4()),
            content=content.replace("\u3000", " "),
            metadata={"file_name": origin_filepath.name}
        )

        return [link_document]

