# -*- coding: utf-8 -*-
"""
ES 索引管理接口：创建/删除/查询索引，与 linkrag 索引结构一致。
"""
from typing import Any
from pydantic import BaseModel
from fastapi import APIRouter

from .component import es_client

router = APIRouter(prefix="/index", tags=["index"])

MAPPINGS = {
    "_source": {"excludes": ["embedding"]},
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
        "metadata": {"type": "object"},
    },
}
SETTINGS = {"number_of_replicas": 1, "refresh_interval": "5s"}


class DBRequest(BaseModel):
    index: str


class DBDocRequest(BaseModel):
    index: str
    doc_id: str


class DBResponse(BaseModel):
    status: int = 200
    msg: Any = None


@router.put("/create")
async def create_index(request: DBRequest) -> DBResponse:
    """创建索引；已存在则返回 200"""
    index = request.index
    if await es_client.es.indices.exists(index=index):
        return DBResponse(status=200, msg=f"Index `{index}` already exists.")
    resp = await es_client.es.indices.create(
        index=index, mappings=MAPPINGS, settings=SETTINGS
    )
    if resp.get("acknowledged", False) and await es_client.es.indices.exists(index=index):
        return DBResponse(status=200, msg="Success")
    return DBResponse(status=0, msg=f"Create index failed. {resp}")


@router.delete("/delete")
async def delete_index(request: DBRequest) -> DBResponse:
    """删除索引"""
    index = request.index
    if not await es_client.es.indices.exists(index=index):
        return DBResponse(status=200, msg=f"Index `{index}` does not exist.")
    resp = await es_client.es.indices.delete(index=index)
    if resp.get("acknowledged", False) and not await es_client.es.indices.exists(index=index):
        return DBResponse(status=200, msg="Success")
    return DBResponse(status=0, msg=f"Delete index failed. {resp}")


@router.get("/info")
async def info(request: DBRequest) -> DBResponse:
    index = request.index
    if not await es_client.es.indices.exists(index=index):
        return DBResponse(status=0, msg=f"Index `{index}` does not exist.")
    resp = await es_client.es.indices.get(index=index)
    return DBResponse(status=200, msg=resp.body)


@router.post("/delete-doc")
async def delete_doc_chunks(request: DBDocRequest) -> DBResponse:
    """按 doc_id 删除指定索引中的文档切片。"""
    index = request.index
    doc_id = (request.doc_id or "").strip()
    if not doc_id:
        return DBResponse(status=0, msg="doc_id is required")
    if not await es_client.es.indices.exists(index=index):
        return DBResponse(status=200, msg=f"Index `{index}` does not exist.")

    resp = await es_client.es.delete_by_query(
        index=index,
        body={"query": {"term": {"doc_id": doc_id}}},
        refresh=True,
        conflicts="proceed",
    )
    return DBResponse(status=200, msg={"deleted": resp.get("deleted", 0)})
