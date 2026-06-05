# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/11 17:13
# @Author  : cuils
# @Description:
"""
from typing import Any, Dict
from pydantic import BaseModel



class SearchResult(BaseModel):
    source: Dict[str, Any]
    score: float


class BaseDBClient:
    def __init__(self, **kwargs):
        pass

    def create(self, **kwargs):
        raise NotImplementedError()

    def insert(self, **kwargs):
        raise NotImplementedError()

    def search(self, **kwargs):
        raise NotImplementedError

    def update(self, **kwargs):
        raise NotImplementedError

    def delete(self, **kwargs):
        raise NotImplementedError

    def info(self):
        raise NotImplementedError


class AsyncBaseDBClient:
    def __init__(self, **kwargs):
        pass

    async def search(self, **kwargs):
        raise NotImplementedError

    async def create(self, **kwargs):
        raise NotImplementedError()

    async def insert(self, **kwargs):
        raise NotImplementedError()

    async def update(self, **kwargs):
        raise NotImplementedError

    async def delete(self, **kwargs):
        raise NotImplementedError

    async def info(self):
        raise NotImplementedError