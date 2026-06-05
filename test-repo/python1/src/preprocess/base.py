# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/6 14:00
# @Author  : cuils
# @Description:
"""
from pydantic import BaseModel
from typing import Union, List, Any, Dict


class LinkDocument(BaseModel):
    """文档信息"""
    doc_id: Union[int, str] = None
    content: str
    images: List[str|Dict[str, Any]] = [] # 图片为base64编码的字符串
    hyperlinks: List[Dict[str, Any]] = [] # 超链接
    comments: List[Dict[str, Any]] = [] # 注释
    charts: List[Dict[str, Any]] = [] # 图表
    metadata: Dict[str, Any] = {}


class Chunk(BaseModel):
    """分块定义"""
    chunk_id: Union[int, str]|None = None
    doc_id: Union[int, str]
    content: str
    embedding: List[float] = None
    embedding_model: str = None
    metadata: Dict[str, Any] = {}