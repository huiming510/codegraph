# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/28 17:15
# @Author  : cuils
# @Description:
知识库操作管理接口
-创建
-删除
-查看
"""
from typing import Any
from pydantic import BaseModel
from fastapi import APIRouter, Query
from starlette import status
from .container import app_container, app_logger

router = APIRouter(prefix="/index", tags=["index"])

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


class DBRequest(BaseModel):
    index: str


class DBDocRequest(BaseModel):
    index: str
    doc_id: str


class DBResponse(BaseModel):
    status: int = status.HTTP_200_OK
    msg: Any = None


@router.put("/create")
async def create_index(request: DBRequest) -> DBResponse:
    """判断索引是否已存在，
        如果存在或新建成功则返回200
        否则返回0
    """
    index = request.index
    if await app_container.es_client.es.indices.exists(index=index):
        return DBResponse(status=status.HTTP_200_OK, msg=f"Index `{index}` already exists.")
    resp = await app_container.es_client.es.indices.create(index=index, mappings=MAPPINGS, settings=SETTINGS)
    if resp.get("acknowledged", False) and await app_container.es_client.es.indices.exists(index=index):
        app_logger.info(f"Create index `{index}` successfully.")
        return DBResponse(status=status.HTTP_200_OK, msg="Success")
    app_logger.info(f"Create index `{index}` failed. {resp}")
    return DBResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=f"Create index failed. {resp}")


@router.delete("/delete")
async def delete_index(index: str = Query(...)) -> DBResponse:
    """删除索引"""
    if not await app_container.es_client.es.indices.exists(index=index):
        return DBResponse(status=status.HTTP_200_OK, msg=f"Index `{index}` does not exist.")
    resp = await app_container.es_client.es.indices.delete(index=index)
    if resp.get("acknowledged", False) and not await app_container.es_client.es.indices.exists(index=index):
        app_logger.info(f"Delete index `{index}` successfully.")
        return DBResponse(status=status.HTTP_200_OK, msg="Success")
    app_logger.info(f"Delete index `{index}` failed. {resp}")
    return DBResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=f"Delete index failed. {resp}")


@router.post("/info")
async def info(request: DBRequest) -> DBResponse:
    index = request.index
    if not await app_container.es_client.es.indices.exists(index=index):
        return DBResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=f"Index `{index}` does not exist.")
    resp = await app_container.es_client.es.indices.get(index=index)
    return DBResponse(status=status.HTTP_200_OK, msg=resp.body)


@router.post("/delete-doc")
async def delete_doc_chunks(request: DBDocRequest) -> DBResponse:
    """按 doc_id 删除指定索引中的文档切片。"""
    index = request.index
    doc_id = (request.doc_id or "").strip()
    if not doc_id:
        return DBResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR, msg="doc_id is required")
    if not await app_container.es_client.es.indices.exists(index=index):
        return DBResponse(status=status.HTTP_200_OK, msg=f"Index `{index}` does not exist.")

    resp = await app_container.es_client.es.delete_by_query(
        index=index,
        body={"query": {"term": {"doc_id": doc_id}}},
        refresh=True,
        conflicts="proceed",
    )
    return DBResponse(status=status.HTTP_200_OK, msg={"deleted": resp.get("deleted", 0)})
