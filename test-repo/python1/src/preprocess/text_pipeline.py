# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/30 10:32
# @Author  : cuils
# @Description:
文本数据处理流水线
"""
from typing import List
from pathlib import Path

from .base import LinkDocument, Chunk
from .chunk.text_splitter import MarkdownTextSplitter
from .doc_parser import WordParser, ExcelParser, PPTParser, PDFParser, XMLParser, TXTParser
from .format_convert import LibreofficeFormatConverter, MinerUFormatConverter

TOKENIZER_DIR = Path(__file__).parent / "tokenizer" / "Qwen3-Embedding-0.6B"


class TextPipeline:
    def __init__(
        self,
        logger,
        chunk_size: int = 4096,
        chunk_overlap: int = 256,
        chunk_strategy: str = "general",
        cache_dir: str = None
    ):
        self.logger = logger
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunk_strategy = chunk_strategy

        # 初始化 格式转换工具
        office_converter = LibreofficeFormatConverter(cache_dir=cache_dir)
        # mineru_converter = MinerUFormatConverter(cache_dir=cache_dir)

        # 初始化 文件解析器
        # TODO：下面实现不好，只能手动一个一个的加parser，后续考虑使用装饰器实现
        excel_parser = ExcelParser(logger, converter=office_converter)
        ppt_parser = PPTParser(logger, converter=office_converter)
        word_parser = WordParser(logger, converter=office_converter)
        # pdf_parser = PDFParser(logger, converter=mineru_converter)
        xml_parser = XMLParser(logger)
        txt_parser = TXTParser(logger)

        self.parser_mapping = {}
        for suffix in word_parser.support_file_formats:
            self.parser_mapping[suffix] = word_parser
        for suffix in excel_parser.support_file_formats:
            self.parser_mapping[suffix] = excel_parser
        # for suffix in pdf_parser.support_file_formats:
        #     self.parser_mapping[suffix] = pdf_parser
        for suffix in ppt_parser.support_file_formats:
            self.parser_mapping[suffix] = ppt_parser
        for suffix in xml_parser.support_file_formats:
            self.parser_mapping[suffix] = xml_parser
        for suffix in txt_parser.support_file_formats:
            self.parser_mapping[suffix] = txt_parser

        # 初始化文本切分工具，默认使用tokenizer分词后的长度进行切分
        # 分块策略，默认为general分块，暂时仅支持general分块
        try:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_DIR)
            self.text_splitter = MarkdownTextSplitter.from_huggingface_tokenizer(
                tokenizer=tokenizer,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
        except:
            self.text_splitter = MarkdownTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )

    def run(self, filepath: str | Path, doc_id: str = None) -> List[Chunk]:
        """解析"""
        filepath = Path(filepath).absolute()
        suffix = filepath.suffix.lstrip(".")

        # 1.文件解析
        if suffix not in self.parser_mapping:
            self.logger.info(
                f"[Error] {filepath.name} - `{suffix}` not supported yet. only {list(self.parser_mapping.keys())}")
            return []
        parser = self.parser_mapping[suffix]
        documents: list[LinkDocument] = parser.parse(filepath, doc_id=doc_id)
        # 2. 图片解析（多模态支持)

        # 3. 分块
        chunks = []
        for document in documents:
            segments = self.text_splitter.split_text(text=document.content)
            # 若document为xlsx的一个sheet，每个sheet的doc_id相同
            sheet_idx = document.metadata.get("sheet_idx", None)
            for i, seg in enumerate(segments, start=1):
                chunk_id = f"{document.doc_id}_chunk_{i}" if sheet_idx is None else f"{document.doc_id}_sheet_{sheet_idx}_chunk_{i}"
                chunk = Chunk(
                    chunk_id=chunk_id,
                    doc_id=document.doc_id,
                    content=seg,
                    metadata=document.metadata
                )
                chunks.append(chunk)

        return chunks