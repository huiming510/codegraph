# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/17
# @Author  : cuils
# @Description: 
"""
import aiohttp
import asyncio
import requests


class VllmEmbedding:
    """VLLM Embedding 服务"""

    def __init__(self, url, model, support_matryoshka=False, dimensions=1024):
        self.url = url
        self.model = model
        self.support_matryoshka = support_matryoshka
        self.dimensions = dimensions

    async def aencode(self, text, **kwargs):
        payload = {
            "model": self.model,
            "input": text
        }
        if self.support_matryoshka and self.dimensions:
            payload["dimensions"] = self.dimensions

        if kwargs:
            payload.update(kwargs)

        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url=self.url, json=payload, headers=headers) as resp:
                    result = await resp.json()
                    return result["data"][0]["embedding"]
            except:
                return None

    async def abatch_encode(self, texts, **kwargs):
        """批量计算不使用prompt"""
        return await asyncio.gather(*[self.aencode(text, **kwargs) for text in texts])

    def encode(self, text, **kwargs):
        """如果是计算query embedding，prompt可以为
        Given a search query, retrieve relevant passages that answer the query。
        query:
        """
        payload = {
            "model": self.model,
            "input": text
        }
        if self.support_matryoshka and self.dimensions:
            payload["dimensions"] = self.dimensions

        if kwargs:
            payload.update(kwargs)

        headers = {"Content-Type": "application/json"}
        return requests.post(url=self.url, json=payload, headers=headers).json()["data"][0]["embedding"]

    def batch_encode(self, texts, **kwargs):
        """批量计算不使用prompt"""
        async_results = asyncio.run(self.abatch_encode(texts, **kwargs))
        return async_results


class OllamaEmbedding:
    """Ollama Embedding 服务"""

    def __init__(self, url, model):
        self.url = url
        self.model = model

    async def aencode(self, text):
        payload = {
            "model": self.model,
            "input": [text]
        }
        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url=self.url, json=payload, headers=headers) as resp:
                    result = await resp.json()
                    return result["embeddings"][0]
            except:
                return None

    async def abatch_encode(self, texts):
        payload = {
            "model": self.model,
            "input": texts
        }
        headers = {"Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url=self.url, json=payload, headers=headers) as resp:
                    result = await resp.json()
                    return result["embeddings"]
            except:
                return None

    def encode(self, text):
        payload = {
            "model": self.model,
            "input": [text]
        }
        headers = {"Content-Type": "application/json"}
        return requests.post(url=self.url, json=payload, headers=headers).json()["embeddings"][0]

    def batch_encode(self, texts):
        payload = {
            "model": self.model,
            "input": texts
        }
        headers = {"Content-Type": "application/json"}
        return requests.post(url=self.url, json=payload, headers=headers).json()["embeddings"]