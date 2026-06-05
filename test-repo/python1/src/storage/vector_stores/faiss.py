# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/13 13:34
# @Author  : cuils
# @Description:
"""
from typing import Dict, List, Optional, Any
from .base import BaseDBClient, AsyncBaseDBClient, SearchResult

try:
    import faiss
except ImportError:
    raise ImportError(
        "Could not import faiss python package. "
        "Please install it with `pip install faiss-gpu` (for CUDA supported GPU) "
        "or `pip install faiss-cpu` (depending on Python version)."
    )