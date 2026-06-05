# -*- coding: utf-8 -*-
"""
# @Time    : 2025/11/13
# @Author  : cuils
# @Description:
NOTE:
ES 增删改查
"""
from elasticsearch import Elasticsearch, AsyncElasticsearch


class ElasticsearchClient:
    def __init__(self, url):
        self.es = Elasticsearch(url)

    def search(self, index, query, embedding=None, top_k=10, method="dense_filter"):
        if method == "dense":
            return self._dense_search(query, embedding, top_k, index)
        elif method == "dense_filter":
            return self._dense_search_with_filter(query, embedding, top_k, index)
        elif method == "hybrid":
            return self._hybrid_search(query, embedding, top_k, index)
        elif method == "sparse":
            raise NotImplementedError
        else:
            raise ValueError(f"Method must be dense, dense_filter, hybrid, sparse, but get {method}")

    def _dense_search(self, query, query_embed, top_k, index):
        """向量搜索，同时存在过滤"""
        if query_embed is None:
            raise ValueError("Query_embed is None")

        knn = {
            "field": "embedding",
            "query_vector": query_embed,
            "k": top_k,
            "num_candidates": 10000
        }

        resp = self.es.search(index=index, knn=knn, source_excludes=["embedding"], size=top_k)
        return resp["took"], resp["hits"]["hits"]

    def _dense_search_with_filter(self, query, query_embed, top_k, index):
        """向量搜索，同时存在过滤"""
        if query_embed is None:
            raise ValueError("Query_embed is None")

        knn = {
            "field": "embedding",
            "query_vector": query_embed,
            "k": top_k,
            "num_candidates": 10000,
            "filter": {
                "bool": {
                    "must": [
                        {"match": {"content": {"query": query, "boost": 5}}},
                    ]
                }
            }
        }

        resp = self.es.search(index=index, knn=knn, source_excludes=["embedding"], size=top_k)
        return resp["took"], resp["hits"]["hits"]

    def _hybrid_search(self, query, query_embed, top_k, index):
        if query_embed is None:
            raise ValueError("Query_embed is None")

        bm = {
            "match": {
                "content": {"query": query, "boost": 0.3}
            }
        }

        knn = {
            "field": "embedding",
            "query_vector": query_embed,
            "k": top_k,
            "num_candidates": 10000
        }

        resp = self.es.search(index=index, knn=knn, query=bm, source_excludes=["embedding"], size=top_k)

        return resp["took"], resp["hits"]["hits"]

    def close(self):
        self.es.close()


class AsyncElasticsearchClient:

    def __init__(self, url):
        self.es = AsyncElasticsearch(url)

    async def search(self, index, query, embedding=None, top_k=10, method="dense_filter"):
        if method == "dense":
            return await self._dense_search(query, embedding, top_k, index)
        elif method == "dense_filter":
            return await self._dense_search_with_filter(query, embedding, top_k, index)
        elif method == "hybrid":
            return await self._hybrid_search(query, embedding, top_k, index)
        elif method == "sparse":
            raise NotImplementedError
        else:
            raise ValueError(f"Method must be dense, dense_filter, hybrid, sparse, but get {method}")

    async def _dense_search(self, query, query_embed, top_k, index):
        """向量搜索，同时存在过滤"""
        if query_embed is None:
            raise ValueError("Query_embed is None")

        knn = {
            "field": "embedding",
            "query_vector": query_embed,
            "k": top_k,
            "num_candidates": 10000
        }

        resp = await self.es.search(index=index, knn=knn, source_excludes=["embedding"], size=top_k)
        return resp["took"], resp["hits"]["hits"]

    async def _dense_search_with_filter(self, query, query_embed, top_k, index):
        """向量搜索，同时存在过滤"""
        if query_embed is None:
            raise ValueError("Query_embed is None")

        knn = {
            "field": "embedding",
            "query_vector": query_embed,
            "k": top_k,
            "num_candidates": 10000,
            "filter": {
                "bool": {
                    "must": [
                        {"match": {"content": {"query": query, "boost": 5}}},
                    ]
                }
            }
        }

        resp = await self.es.search(index=index, knn=knn, source_excludes=["embedding"], size=top_k)
        return resp["took"], resp["hits"]["hits"]

    async def _hybrid_search(self, query, query_embed, top_k, index):
        if query_embed is None:
            raise ValueError("Query_embed is None")

        bm = {
            "match": {
                "content": {"query": query, "boost": 0.3}
            }
        }

        knn = {
            "field": "embedding",
            "query_vector": query_embed,
            "k": top_k,
            "num_candidates": 10000
        }

        resp = await self.es.search(index=index, knn=knn, query=bm, source_excludes=["embedding"], size=top_k)

        return resp["took"], resp["hits"]["hits"]

    async def close(self):
        await self.es.close()