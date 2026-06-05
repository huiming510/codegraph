# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/12 10:35
# @Author  : cuils
# @Description:
"""
from typing import Dict, List, Optional, Any
from .base import SearchResult, BaseDBClient, AsyncBaseDBClient

try:
    import pymilvus  # noqa: F401
    from pymilvus import DataType, MilvusClient, AsyncMilvusClient
except ImportError:
    raise ImportError(
        "The 'pymilvus' library is required."
        "Please install it using 'pip install pymilvus' or uv add pymilvus."
    )


class MilvusDBClient(BaseDBClient):
    def __init__(
        self,
        url: str = "milvus.db",
        token: Optional[str] = None,
        embedding_dims: Optional[int] = 1024,
        **kwargs
    ) -> None:
        """
        初始化 Milvus 向量数据库
        Args:
            url: Full URL, local模式使用
            token: server用的 token或api_key, 本地的不需要，默认为None
            embedding_dims: embedding模型输出维度，默认1024
        """
        super().__init__()
        self.embedding_dims = embedding_dims
        self.client = MilvusClient(uri=url, token=token, db_name="default")

    def create(self, collection_name: str) -> None:
        """创建新的向量索引"""
        if self.client.has_collection(collection_name):
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="chunk_id", datatype=DataType.VARCHAR, is_primary=True, max_length=512)
        schema.add_field(field_name="doc_id", datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=1024*1024,
                         enable_analyzer=True, analyzer_params={"type": "japanese"})
        schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=self.embedding_dims)
        schema.add_field(field_name="embedding_model", datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="metadata", datatype=DataType.JSON)

        index = self.client.prepare_index_params(
            field_name="embedding",
            index_type="AUTOINDEX",
            index_name="default",
            metric_type="IP"
        )
        self.client.create_collection(collection_name, schema=schema, index_params=index)

    def search(
        self,
        collection_name: str,
        query: Optional[str],
        embedding: Optional[List[float]],
        top_k: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """搜索"""
        if not self.client.has_collection(collection_name):
            raise Exception(f"Collection {collection_name} does not exist!")

        hits = self.client.search(
            collection_name=collection_name,
            anns_field="embedding",
            data=[embedding],
            filter=f"TEXT_MATCH(content, '{query}')" if kwargs.get("method") == "hybrid" else None,
            limit=top_k,
            output_fields=["chunk_id", "doc_id", "content", "embedding_model", "metadata"]
        )

        results = []

        for hit in hits:
            result = SearchResult(
                source=hit["entity"],
                score=hit["distance"]
            )
            results.append(result)
        return results

    def insert(self, collection_name: str, unique_id: str, data: Dict[str, Any]) -> None:
        """
        插入数据
        Args:
            collection_name: 索引名称
            unique_id: 唯一id
            data: 数据

        Returns:
            None
        """
        if not self.client.has_collection(collection_name):
            raise Exception(f"Collection {collection_name} does not exist!")

        self.client.insert(collection_name=collection_name, data=data)

    def update(self, collection_name: str, unique_id: str, data: Dict[str, Any]) -> None:
        """更新插入数据"""
        if not self.client.has_collection(collection_name):
            raise Exception(f"Collection {collection_name} does not exist!")

        self.client.upsert(collection_name=collection_name, data=data)

    def delete(self, collection_name: str, unique_id: str) -> Optional[Dict[str, Any]]:
        """删除数据"""
        if not self.client.has_collection(collection_name):
            raise Exception(f"Collection {collection_name} does not exist!")


        hits = self.client.get(collection_name=collection_name, ids=unique_id)
        if len(hits) == 0:
            return None

        self.client.delete(collection_name=collection_name, ids=unique_id)

        return hits[0]

    def info(self):
        return self.client.list_collections()


class AsyncMilvusDBClient(AsyncBaseDBClient):
    def __init__(
        self,
        url: str = "milvus.db",
        token: Optional[str] = None,
        embedding_dims: Optional[int] = 1024,
        **kwargs
    ) -> None:
        """
        初始化 Milvus 向量数据库
        Args:
            url: Full URL, local模式使用
            token: server用的 token或api_key, 本地的不需要，默认为None
            embedding_dims: embedding模型输出维度，默认1024
        """
        super().__init__()
        self.embedding_dims = embedding_dims
        self.client = AsyncMilvusClient(uri=url, token=token, db_name="default")

    async def create(self, collection_name: str) -> None:
        """创建新的向量索引"""
        if await self.client.has_collection(collection_name):
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
        schema.add_field(field_name="chunk_id", datatype=DataType.VARCHAR, is_primary=True, max_length=512)
        schema.add_field(field_name="doc_id", datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=1024*1024,
                         enable_analyzer=True, analyzer_params={"type": "japanese"})
        schema.add_field(field_name="embedding", datatype=DataType.FLOAT_VECTOR, dim=self.embedding_dims)
        schema.add_field(field_name="embedding_model", datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="metadata", datatype=DataType.JSON)

        index = self.client.prepare_index_params(
            field_name="embedding",
            index_type="AUTOINDEX",
            index_name="default",
            metric_type="IP"
        )
        await self.client.create_collection(collection_name, schema=schema, index_params=index)

    async def search(
        self,
        collection_name: str,
        query: Optional[str],
        embedding: Optional[List[float]],
        top_k: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """搜索"""
        if not await self.client.has_collection(collection_name):
            raise Exception(f"Collection {collection_name} does not exist!")

        hits = await self.client.search(
            collection_name=collection_name,
            anns_field="embedding",
            data=[embedding],
            filter=f"TEXT_MATCH(content, '{query}')" if kwargs.get("method") == "hybrid" else None,
            limit=top_k,
            output_fields=["chunk_id", "doc_id", "content", "embedding_model", "metadata"]
        )

        results = []

        for hit in hits:
            result = SearchResult(
                source=hit["entity"],
                score=hit["distance"]
            )
            results.append(result)
        return results

    async def insert(self, collection_name: str, unique_id: str, data: Dict[str, Any]) -> None:
        """
        插入数据
        Args:
            collection_name: 索引名称
            unique_id: 唯一id
            data: 数据

        Returns:
            None
        """
        if not await self.client.has_collection(collection_name):
            raise Exception(f"Collection {collection_name} does not exist!")

        await self.client.insert(collection_name=collection_name, data=data)

    async def update(self, collection_name: str, unique_id: str, data: Dict[str, Any]) -> None:
        """更新插入数据"""
        if not await self.client.has_collection(collection_name):
            raise Exception(f"Collection {collection_name} does not exist!")

        await self.client.upsert(collection_name=collection_name, data=data)

    async def delete(self, collection_name: str, unique_id: str) -> Optional[Dict[str, Any]]:
        """删除数据"""
        if not await self.client.has_collection(collection_name):
            raise Exception(f"Collection {collection_name} does not exist!")

        hits = await self.client.get(collection_name=collection_name, ids=unique_id)
        if len(hits) == 0:
            return None

        await self.client.delete(collection_name=collection_name, ids=unique_id)

        return hits[0]

    async def info(self):
        return await self.client.list_collections()