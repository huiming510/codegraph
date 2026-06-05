# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/13 17:00
# @Author  : cuils
# @Description:
"""
import os
from pathlib import Path

CONVERT_CACHE_DIR = Path(__file__).absolute().parent.parent / "cache"


class BaseFormatConverter:
    def __init__(self, cache_dir=None):
        if cache_dir is None:
            cache_dir = CONVERT_CACHE_DIR
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)

    def convert(self, **kwargs):
        raise NotImplementedError
