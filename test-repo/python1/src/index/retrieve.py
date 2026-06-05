# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/18
# @Author  : cuils
# @Description: 
"""
import asyncio
from .embed import VllmEmbedding
from .es_client import ElasticsearchClient, AsyncElasticsearchClient


class Retriever:
    def __init__(
            self,
            embedding_client: VllmEmbedding,
            es_client: ElasticsearchClient
    ):
        self.embedding_client = embedding_client
        self.es_client = es_client

    def retrieve(self, index, query, top_k, method="dense_filter"):
        query = f"Given a search query, retrieve relevant passages that answer the query。\n\n{query}"

        q_embed = self.embedding_client.encode(query)

        elapsed, hits = self.es_client.search(query=query, embedding=q_embed, top_k=top_k, method=method, index=index)

        sources = []

        for hit in hits:
            source = hit["_source"]
            source["score"] = hit["_score"]

            sources.append(source)

        return elapsed, sources


class AsyncRetriever:
    def __init__(
            self,
            embedding_client: VllmEmbedding,
            es_client: AsyncElasticsearchClient
    ):
        self.embedding_client = embedding_client
        self.es_client = es_client

    async def retrieve(self, index, query, top_k, method="dense_filter"):
        query = f"Given a search query, retrieve relevant passages that answer the query。\n\n{query}"

        q_embed = await self.embedding_client.aencode(query)

        elapsed, hits = await self.es_client.search(query=query, embedding=q_embed, top_k=top_k, method=method, index=index)

        sources = []

        for hit in hits:
            source = hit["_source"]
            source["score"] = hit["_score"]

            sources.append(source)

        return elapsed, sources

    async def parallel_retrieve(self, index, queries, top_k, method="dense_filter"):
        tasks = [
            self.retrieve(index, query, top_k, method)
            for query in queries
        ]
        return await asyncio.gather(*tasks)