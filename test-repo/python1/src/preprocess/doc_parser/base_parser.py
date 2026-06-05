# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/8 16:37
# @Author  : cuils
# @Description:
"""
import logging
from pathlib import Path


class BaseParser:
    """
    文档解析器：
    logger: 日志
    """
    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def parse(self, filepath: str | Path, doc_id: str=None):
        raise NotImplementedError