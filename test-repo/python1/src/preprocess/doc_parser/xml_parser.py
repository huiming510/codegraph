# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/30 16:56
# @Author  : dingsh
# @Description:
"""
import re
import uuid
import xml.etree.ElementTree as ET
from typing import List
from pathlib import Path
from .base_parser import BaseParser
from ..base import LinkDocument


# 标签到Markdown前缀的映射表
TAG_PREFIX_MAP = {
    "Law": '',
    'LawBody': '',
    'TOC': '\n\n# ',  # 目次标题前缀
    'TOCLabel': '',  # 目次内容
    'TOCChapter': '\n- ',  # 目次章节前加列表符号
    'TOCSection': '\n- ',  # 目次节前加列表符号
    'TOCSupplProvision': '\n- ',  # 目次附则前加列表符号
    'SupplProvisionLabel': '',  # 附则标签处理为普通文本
    'Chapter': '\n\n# ',
    'ChapterTitle': '',
    'Section': '\n\n## ',  # 章节间的节，二级标题
    'SectionTitle': '',
    'MainProvision': '',  # 主要规定部分不输出标签
    'Article': '\n\n### ',
    'ArticleCaption': '',  # 文章标题说明紧跟标题
    'ArticleTitle': '\n',  # 文章标题换行显示
    'Paragraph': '',
    'ParagraphNum': '\n\n　　',  # 段落编号前换行并缩进
    'ParagraphSentence': '',
    'Item': '\n- ',
    'ItemTitle': '**',
    'ItemSentence': '',
    'Column': ' ',  # Column标签之间加空格
    'Subitem1': '\n  - ',
    'Subitem1Title': '**',
    'Subitem1Sentence': '',
    'Subitem2': '\n    - ',
    'Subitem2Title': '**',
    'Subitem2Sentence': '',
    'Subitem3': '\n      - ',
    'Subitem3Title': '**',
    'Subitem3Sentence': '',
    'Sentence': '',
    'SupplProvision': '\n\n---\n\n**附　則**\n\n',
    'LawTitle': '# ',  # 法律标题作为顶级标题
    'LawNum': '',  # 法律编号
}

# 标签到Markdown后缀的映射表
TAG_SUFFIX_MAP = {
    'ItemTitle': '**',
    'Subitem1Title': '**',
    'Subitem2Title': '**',
    'Subitem3Title': '**',
    'SupplProvision': '\n\n---\n',
    'Article': '',  # Article后不需要额外换行
    'Chapter': '\n',  # Chapter后换行
    'Section': '\n',  # Section后换行
    'ParagraphNum': '',
    'ArticleTitle': '',
    'LawTitle': '\n',  # 法律标题后换行
    'ArticleCaption': '\n',  # ArticleCaption后换行
    'LawNum': '\n',  # 法律编号后换行
}


class XMLParser(BaseParser):
    def __init__(self, logger):
        super().__init__(logger)

    @property
    def support_file_formats(self) -> List[str]:
        return ["xml"]

    def parse(self, filepath: str | Path, doc_id=None) -> List[LinkDocument]:
        # 解析XML文件
        filepath = Path(filepath).absolute()
        suffix = filepath.suffix.lstrip(".").lower()
        if suffix not in self.support_file_formats:
            raise ValueError(f"XML Parser only supports {self.support_file_formats}, but got {suffix}")

        tree = ET.parse(filepath)
        root = tree.getroot()

        # 存储输出行
        output_lines = []

        # 递归转换XML元素
        def _convert_element(element):
            tag = element.tag

            # 添加前缀
            prefix = TAG_PREFIX_MAP.get(tag, '')
            if prefix:
                output_lines.append(prefix)

            # 特殊处理：对于ArticleCaption和ArticleTitle，使它们在同一行
            if tag == 'ArticleCaption':
                # ArticleCaption的文本内容放在前缀后，不换行
                if element.text and element.text.strip():
                    output_lines.append(element.text.strip())
            elif tag == 'ArticleTitle':
                # ArticleTitle前面有个换行，然后是标题内容
                if element.text and element.text.strip():
                    output_lines.append(element.text.strip())
            else:
                # 处理其他标签的文本内容
                if element.text and element.text.strip():
                    output_lines.append(element.text.strip())

            for child in element:
                _convert_element(child)

            suffix = TAG_SUFFIX_MAP.get(tag, '')
            if suffix:
                output_lines.append(suffix)

            if element.tail and element.tail.strip():
                output_lines.append(element.tail.strip())

        # 开始转换
        _convert_element(root)

        # 生成最终Markdown内容
        markdown = ''.join(output_lines)

        # 优化换行格式 - 移除过多连续的换行

        markdown = re.sub(r'\n\s*\n\s*\n+', '\n\n', markdown)

        document = LinkDocument(
            doc_id=doc_id or str(uuid.uuid4()),
            content=markdown,
            metadata={"file_name": filepath.name}
        )
        return [document]
