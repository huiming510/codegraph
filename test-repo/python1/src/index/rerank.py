# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/4 11:03
# @Author  : cuils
# @Description:
"""
import aiohttp
import asyncio
import requests


class VllmReranker:
    """vllm 部署的 reranker 模型"""

    def __init__(self, url, model, llm_arch=False):
        self.url = url
        self.model = model
        self.llm_arch = llm_arch

    def encode(self, query, documents: list[str]) -> list[float]:
        if self.llm_arch:
            query, documents = self.preprocess(query, documents)
        payload = {
            "query": query,
            "documents": documents,
        }
        resp = requests.post(self.url, json=payload).json()
        if isinstance(resp, list):
            return resp
        if isinstance(resp, dict) and "results" in resp:
            return [
                r.get("relevance_score", r) if isinstance(r, dict) else r
                for r in resp["results"]
            ]
        return []

    async def aencode(self, query, documents: list[str]):
        if self.llm_arch:
            query, documents = self.preprocess(query, documents)
        payload = {
            "query": query,
            "documents": documents,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, json=payload) as response:
                resp = await response.json()
                # 兼容不同返回格式：list 直接为分数，或 {"results": [{"relevance_score": x}]}
                if isinstance(resp, list):
                    return resp
                if isinstance(resp, dict) and "results" in resp:
                    return [
                        r.get("relevance_score", r) if isinstance(r, dict) else r
                        for r in resp["results"]
                    ]
                return []

    def preprocess(self, query, documents: list[str]):
        """Qwen3 Reranker model"""
        prefix = '<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. Note that the answer can only be "yes" or "no".<|im_end|>\n<|im_start|>user\n'
        suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"

        query_template = "{prefix}<Instruct>: {instruction}\n<Query>: {query}\n"
        document_template = "<Document>: {doc}{suffix}"

        instruction = "Given a web search query, retrieve relevant passages that answer the query"

        query = query_template.format(prefix=prefix, instruction=instruction, query=query)

        documents = [document_template.format(doc=doc, suffix=suffix) for doc in documents]

        return query, documents



if __name__ == '__main__':
    reranker_client = VllmReranker(
        url="http://192.168.10.187:5003/v1/rerank",
        model="bge-reranker-v2-m3",
    )

    query = "What is the capital of China?"

    documents = [
        "The capital of China is Beijing.",
        "Gravity is a force that attracts two bodies towards each other. It gives weight to physical objects and is responsible for the movement of planets around the sun.",
    ]

    resp = asyncio.run(reranker_client.aencode(query, documents))
    print(resp)