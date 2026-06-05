# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/12 11:35
# @Author  : cuils
# @Description:
"""
from typing import List, Optional, Dict, Any
from elasticsearch import Elasticsearch, AsyncElasticsearch, NotFoundError

from .base import SearchResult, BaseDBClient, AsyncBaseDBClient

# 索引
MAPPINGS = {
    "_source": {
        "excludes": ["embedding"]
    },
    "properties": {
        "chunk_id": {"type": "keyword"},
        "doc_id": {"type": "keyword"},
        "content": {"type": "text", "analyzer": "kuromoji"},
        "embedding": {
            "type": "dense_vector",
            "dims": 1024,
            "index": True,
            "similarity": "dot_product",
            "index_options": {"type": "hnsw", "m": 8, "ef_construction": 100},
        },
        "embedding_model": {"type": "keyword"},
        "metadata": {"type": "object"}
    }
}
SETTINGS = {
    "number_of_replicas": 0,
    "index.refresh_interval": "5s"
}


class ElasticsearchDBClient(BaseDBClient):
    def __init__(
        self,
        url: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        super().__init__()
        self.client = Elasticsearch(url, http_auth=(user, password))

    def search(
        self,
        index: str,
        query: Optional[str],
        embedding: Optional[List[float]] = None,
        top_k: int = 10,
        method: str = "dense"
    ) -> List[SearchResult]:
        """
        es 搜索
        Args:
            index: 索引名称，必选
            query: 搜索query，若仅向量搜索，可选
            embedding: query向量，若仅稀疏检索，可选
            top_k: 召回数量
            method: 搜索方式：仅向量搜索、带过滤器的向量搜索、混合搜索、稀疏搜索

        Returns:
            搜索结果列表
        """
        if not self.client.indices.exists(index=index):
            raise Exception(f"Index {index} does not exist")

        if method == "dense":
            hits = self._dense_search(index, query, embedding, top_k)
        elif method == "dense_filter":
            hits = self._dense_search_with_filter(index, query, embedding, top_k)
        elif method == "hybrid":
            hits = self._hybrid_search(index, query, embedding, top_k)
        elif method == "sparse":
            hits = self._bm25_search(index, query, embedding, top_k)
        else:
            raise ValueError(f"Method must be dense, dense_filter, hybrid, sparse, but get {method}")

        results = []
        for hit in hits:
            source = hit["_source"]
            score = hit["_score"]
            result = SearchResult(source=source, score=score)
            results.append(result)
        return results

    def _dense_search(self, index: str, query: Optional[str], query_embed: List[float], top_k: int = 20):
        """向量搜索，同时存在过滤"""
        if query_embed is None:
            raise ValueError("Query_embed is None")

        knn = {
            "field": "embedding",
            "query_vector": query_embed,
            "k": top_k,
            "num_candidates": 10000
        }

        resp = self.client.search(index=index, knn=knn, source_excludes=["embedding"], size=top_k)
        return resp["hits"]["hits"]

    def _dense_search_with_filter(self, index: str, query: str, query_embed: List[float], top_k: int = 20):
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

        resp = self.client.search(index=index, knn=knn, source_excludes=["embedding"], size=top_k)
        return resp["hits"]["hits"]

    def _hybrid_search(self, index: str, query: str, query_embed: List[float], top_k: int = 20):
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

        resp = self.client.search(index=index, knn=knn, query=bm, source_excludes=["embedding"], size=top_k)

        return resp["hits"]["hits"]

    def _bm25_search(self, index: str, query: str, query_embed: Optional[List[float]], top_k: int = 20):
        bm = {
            "match": {
                "content": {"query": query}
            }
        }
        resp = self.client.search(index=index, query=bm, source_excludes=["embedding"], size=top_k)
        return resp["hits"]["hits"]

    def create(self, index: str) -> None:
        """
        创建索引
        Args:
            index: 索引名称
        Returns:
            None
        """
        if self.client.indices.exists(index=index):
            return
        self.client.indices.create(index=index, mappings=MAPPINGS, settings=SETTINGS)

    def insert(self, index: str, unique_id: str, data: Dict[str, Any]) -> None:
        """
        插入数据
        Args:
            index: 索引名称
            unique_id: 该数据唯一id
            data: 数据

        Returns:
            None
        """
        if not self.client.indices.exists(index=index):
            raise Exception(f"Index {index} does not exist")

        self.client.index(
            index=index,
            id=unique_id,
            body=data
        )

    def update(self, index: str, unique_id: str, data: Dict[str, Any]) -> None:
        """
        es更新数据等同于插入，会自动更新版本
        Args:
            index: 要更新的索引名称
            unique_id: 该数据的唯一id
            data: 数据，dict
        Returns:
            None
        """
        if not self.client.indices.exists(index=index):
            raise Exception(f"Index {index} does not exist")

        self.insert(index, unique_id, data)

    def delete(self, index: str, unique_id: str) -> Optional[Dict[str, Any]]:
        """
        删除数据
        Args:
            index: 索引名称
            unique_id: 要删除的数据唯一id
        Returns:
            删除的数据信息
        """
        if not self.client.indices.exists(index=index):
            raise Exception(f"Index {index} does not exist")

        try:
            data = self.client.get(index=index, id=unique_id)
        except NotFoundError:
            return None

        self.client.delete(index=index, id=unique_id)
        return data["_source"]

    def info(self) -> Dict[str, Any]:
        """
        返回 数据库信息
        Returns:
        """
        return self.client.info()


class AsyncElasticsearchDBClient(AsyncBaseDBClient):
    def __init__(
        self,
        url: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        super().__init__()
        self.client = AsyncElasticsearch(url, http_auth=(user, password))

    async def search(
        self,
        index: str,
        query: Optional[str],
        embedding: Optional[List[float]] = None,
        top_k: int = 10,
        method: str = "dense"
    ) -> List[SearchResult]:
        """
        es 搜索
        Args:
            index: 索引名称，必选
            query: 搜索query，若仅向量搜索，可选
            embedding: query向量，若仅稀疏检索，可选
            top_k: 召回数量
            method: 搜索方式：仅向量搜索、带过滤器的向量搜索、混合搜索、稀疏搜索

        Returns:
            搜索结果列表
        """
        if not await self.client.indices.exists(index=index):
            raise Exception(f"Index {index} does not exist")

        if method == "dense":
            hits = await self._dense_search(index, query, embedding, top_k)
        elif method == "dense_filter":
            hits = await self._dense_search_with_filter(index, query, embedding, top_k)
        elif method == "hybrid":
            hits = await self._hybrid_search(index, query, embedding, top_k)
        elif method == "sparse":
            hits = await self._bm25_search(index, query, embedding, top_k)
        else:
            raise ValueError(f"Method must be dense, dense_filter, hybrid, sparse, but get {method}")

        results = []
        for hit in hits:
            source = hit["_source"]
            score = hit["_score"]
            result = SearchResult(source=source, score=score)
            results.append(result)
        return results

    async def _dense_search(self, index: str, query: Optional[str], query_embed: List[float], top_k: int = 20):
        """向量搜索，同时存在过滤"""
        if query_embed is None:
            raise ValueError("Query_embed is None")

        knn = {
            "field": "embedding",
            "query_vector": query_embed,
            "k": top_k,
            "num_candidates": 10000
        }

        resp = await self.client.search(index=index, knn=knn, source_excludes=["embedding"], size=top_k)
        return resp["hits"]["hits"]

    async def _dense_search_with_filter(self, index: str, query: str, query_embed: List[float], top_k: int = 20):
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

        resp = await self.client.search(index=index, knn=knn, source_excludes=["embedding"], size=top_k)
        return resp["hits"]["hits"]

    async def _hybrid_search(self, index: str, query: str, query_embed: List[float], top_k: int = 20):
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

        resp = await self.client.search(index=index, knn=knn, query=bm, source_excludes=["embedding"], size=top_k)

        return resp["hits"]["hits"]

    async def _bm25_search(self, index: str, query: str, query_embed: Optional[List[float]], top_k: int = 20):
        bm = {
            "match": {
                "content": {"query": query}
            }
        }
        resp = await self.client.search(index=index, query=bm, source_excludes=["embedding"], size=top_k)
        return resp["hits"]["hits"]

    async def create(self, index: str) -> None:
        """
        创建索引
        Args:
            index: 索引名称
        Returns:
            None
        """
        if await self.client.indices.exists(index=index):
            return
        await self.client.indices.create(index=index, mappings=MAPPINGS, settings=SETTINGS)

    async def insert(self, index: str, unique_id: str, data: Dict[str, Any]) -> None:
        """
        插入数据
        Args:
            index: 索引名称
            unique_id: 该数据唯一id
            data: 数据

        Returns:
            None
        """
        if not await self.client.indices.exists(index=index):
            raise Exception(f"Index {index} does not exist")

        await self.client.index(index=index, id=unique_id, body=data)

    async def update(self, index: str, unique_id: str, data: Dict[str, Any]) -> None:
        """
        es更新数据等同于插入，会自动更新版本
        Args:
            index: 要更新的索引名称
            unique_id: 该数据的唯一id
            data: 数据，dict
        Returns:
            None
        """
        if not await self.client.indices.exists(index=index):
            raise Exception(f"Index {index} does not exist")

        await self.insert(index, unique_id, data)

    async def delete(self, index: str, unique_id: str) -> Optional[Dict[str, Any]]:
        """
        删除数据
        Args:
            index: 索引名称
            unique_id: 要删除的数据唯一id
        Returns:
            删除的数据信息
        """
        if not await self.client.indices.exists(index=index):
            raise Exception(f"Index {index} does not exist")

        try:
            data = await self.client.get(index=index, id=unique_id)
        except NotFoundError:
            raise Exception(f"`{unique_id}` does not exist in index {index}")

        await self.client.delete(index=index, id=unique_id)
        return data["_source"]

    async def info(self) -> Dict[str, Any]:
        """
        返回 数据库信息
        Returns:
        """
        return await self.client.info()
