# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/6 09:13
# @Author  : cuils
# @Description:
chroma向量数据库
chromadb local模式底层使用的是sqlite，因此不存在async
如果使用async，需使用 server模式
"""
from typing import Dict, List, Optional, Any
from .base import BaseDBClient, AsyncBaseDBClient, SearchResult

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.errors import NotFoundError
except ImportError:
    raise ImportError(
        "The 'chromadb' library is required."
        "Please install chromadb using `pip install chromadb` or `uv add chromadb`"
    )


class ChromaDBClient(BaseDBClient):
    def __init__(
        self,
        client: Optional[chromadb.Client] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None
    ):
        """
        初始化 Chromadb向量数据库
        Args:
            client: 已经存在的 client 实例，默认None
            host: chromadb server的IP地址
            port: chromadb server的端口号
            path: 本地 chromadb库路径地址
        """
        super().__init__()
        if client:
            self.client = client
        else:
            # 初始化本地或服务client
            self.settings = Settings(anonymized_telemetry=False)
            if host and port:
                self.settings.chroma_server_host = host
                self.settings.chroma_server_http_port = port
                self.settings.chroma_api_impl = "chromadb.api.fastapi.FastAPI"
            else:
                if path is None:
                    path = "chromadb"

            self.settings.persist_directory = path
            self.settings.is_persistent = True

            self.client = chromadb.Client(self.settings)

    def search(
        self,
        collection_name: str,
        query: Optional[str],
        embedding: List[float],
        top_k: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """
        搜索
        Args:
            collection_name: 索引名称
            query: 搜索query，可选，如果没有embedding，chroma会使用内置的embedding模型进行向量化
            embedding: query embedding，必选
            top_k: 返回文档数量
            kwargs: 其他参数，
                where: metadata 元数据过滤 相当于对metadata的字段进行精确匹配，如：
                    {"category": {"$eq": "AI"}} 表示 category 为 AI
                    多条件匹配，如
                    {
                        "$and": [
                            {"category": {"$eq": "AI"}},
                            {"year": {"$gt": 2021}}
                        ]
                    }
                    表示类别category为 AI 且 年份year大于2021
                where_documents: 文档内容过滤 相当于对document内容进行模糊匹配，如
                    {"$contains": "RAG"} 表示文档中包含 RAG
        Returns:
            结果列表
        """
        try:
            collection = self.client.get_collection(collection_name)
        except NotFoundError:
            raise Exception(f"Collection {collection_name} does not exist")

        hits = collection.query(
            query_embeddings=[embedding],
            query_texts=[query],
            where=kwargs.get("where", None),
            where_document=kwargs.get("where", None),
            n_results=top_k
        )

        results = []

        for i in range(len(hits["ids"][0])):
            data = {}
            for metadata in hits["metadatas"][0]:
                data.update(metadata)
            data["content"] = hits["documents"][0][i]
            score = hits["distances"][0][i]
            result = SearchResult(
                source=data,
                score=score,
            )
            results.append(result)
        return results

    def create(self, collection_name: str) -> None:
        self.client.get_or_create_collection(
            name=collection_name,
            configuration={
                "hnsw": {
                    "space": "cosine"
                }
            }
        )

    def insert(self, collection_name: str, unique_id: str, data: Dict[str, Any]) -> None:
        """
        插入数据
        Args:
            collection_name: 索引名称
            unique_id: 数据唯一id
            data: 数据

        Returns:
            None
        """
        metadata = {}
        for k in data:
            if k == "content" or k == "embedding":
                continue
            metadata[k] = data[k]

        try:
            collection = self.client.get_collection(collection_name)
        except NotFoundError:
            raise Exception(f"Collection {collection_name} does not exist")

        collection.add(
            ids=[unique_id],
            documents=[data.get("content")],
            embeddings=[data.get("embedding")],
            metadatas=[metadata]
        )

    def update(self, collection_name: str, unique_id: str, data: Dict[str, Any]) -> None:
        self.insert(collection_name, unique_id, data)

    def delete(self, collection_name: str, unique_id: str) -> Optional[Dict[str, Any]]:
        """
        删除数据
        Args:
            collection_name: 索引名称
            unique_id: 唯一id
        Returns:
            返回删除的数据
        """
        try:
            collection = self.client.get_collection(collection_name)
        except NotFoundError:
            raise Exception(f"Collection {collection_name} does not exist")

        data = collection.get(ids=[unique_id])
        if not data.get("ids"):
            return None

        collection.delete(ids=[unique_id])

        return data

    def info(self) -> List[str]:
        return [col.name for col in self.client.list_collections()]


class AsyncChromaDBClient(AsyncBaseDBClient):
    def __init__(
        self,
        client: Optional[chromadb.Client] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        **kwargs
    ):
        """
        初始化 Chromadb向量数据库
        Args:
            client: 已经存在的 client 实例，默认None
            host: chromadb server的IP地址
            port: chromadb server的端口号
        """
        super().__init__()
        self.client = None
        self.host = host
        self.port = port

        if client:
            self.client = client

        if self.client is None and (not self.host or not self.port):
            raise Exception("AsyncChromaDB is ONLY in server mode, the server host and port MUST be provided.")

    async def connect(self):
        self.client = await chromadb.AsyncHttpClient(host=self.host, port=self.port)

    async def search(
        self,
        collection_name: str,
        query: Optional[str],
        embedding: List[float],
        top_k: int = 10,
        **kwargs
    ) -> List[SearchResult]:
        """
        搜索
        Args:
            collection_name: 索引名称
            query: 搜索query，可选，如果没有embedding，chroma会使用内置的embedding模型进行向量化
            embedding: query embedding，必选
            top_k: 返回文档数量
            kwargs: 其他参数，
                where: metadata 元数据过滤 相当于对metadata的字段进行精确匹配，如：
                    {"category": {"$eq": "AI"}} 表示 category 为 AI
                    多条件匹配，如
                    {
                        "$and": [
                            {"category": {"$eq": "AI"}},
                            {"year": {"$gt": 2021}}
                        ]
                    }
                    表示类别category为 AI 且 年份year大于2021
                where_documents: 文档内容过滤 相当于对document内容进行模糊匹配，如
                    {"$contains": "RAG"} 表示文档中包含 RAG
        Returns:
            结果列表
        """
        try:
            collection = await self.client.get_collection(collection_name)
        except NotFoundError:
            raise Exception(f"Collection {collection_name} does not exist")

        hits = await collection.query(
            query_embeddings=[embedding],
            query_texts=[query],
            where=kwargs.get("where", None),
            where_document=kwargs.get("where", None),
            n_results=top_k
        )

        results = []

        for i in range(len(hits["ids"][0])):
            data = {}
            for metadata in hits["metadatas"][0]:
                data.update(metadata)
            data["content"] = hits["documents"][0][i]
            score = hits["distances"][0][i]
            result = SearchResult(
                source=data,
                score=score,
            )
            results.append(result)
        return results

    async def create(self, collection_name: str) -> None:
        await self.client.get_or_create_collection(
            name=collection_name,
            configuration={
                "hnsw": {
                    "space": "cosine"
                }
            }
        )

    async def insert(self, collection_name: str, unique_id: str, data: Dict[str, Any]) -> None:
        """
        插入数据
        Args:
            collection_name: 索引名称
            unique_id: 数据唯一id
            data: 数据

        Returns:
            None
        """
        metadata = {}
        for k in data:
            if k == "content" or k == "embedding":
                continue
            metadata[k] = data[k]

        try:
            collection = await self.client.get_collection(collection_name)
        except NotFoundError:
            raise Exception(f"Collection {collection_name} does not exist")

        await collection.add(
            ids=[unique_id],
            documents=[data.get("content")],
            embeddings=[data.get("embedding")],
            metadatas=[metadata]
        )

    async def update(self, collection_name: str, unique_id: str, data: Dict[str, Any]) -> None:
        await self.insert(collection_name, unique_id, data)

    async def delete(self, collection_name: str, unique_id: str) -> Optional[Dict[str, Any]]:
        """
        删除数据
        Args:
            collection_name: 索引名称
            unique_id: 唯一id
        Returns:
            返回删除的数据
        """
        try:
            collection = await self.client.get_collection(collection_name)
        except NotFoundError:
            raise Exception(f"Collection {collection_name} does not exist")

        data = await collection.get(ids=[unique_id])
        if not data.get("ids"):
            return None

        await collection.delete(ids=[unique_id])

        return data

    async def info(self) -> List[str]:
        return [col.name for col in await self.client.list_collections()]
