# -*- coding: utf-8 -*-
"""
Backend 侧根据「ES 环境配置」直接连接 ES，按知识库 es_id 创建索引。
与解析服务 src/server/db.py 的索引结构一致，解析后的文档写入该索引。
"""
from typing import Optional

from elasticsearch import AsyncElasticsearch
from logger import logger


# 与 src/server/db.py 保持一致，保证解析服务写入的文档结构兼容
ES_INDEX_MAPPINGS = {
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
ES_INDEX_SETTINGS = {
    "number_of_replicas": 1,
    "refresh_interval": "5s",
}


def _build_es_client(es_config: dict) -> Optional[AsyncElasticsearch]:
    """
    根据 ES 配置构建 AsyncElasticsearch 客户端。
    es_config 需含: elasticsearch_url, 可选 elasticsearch_username, elasticsearch_password。
    """
    url = (es_config.get("elasticsearch_url") or "").strip()
    if not url:
        return None
    username = (es_config.get("elasticsearch_username") or "").strip()
    password = (es_config.get("elasticsearch_password") or "").strip()

    # 使用 hosts 列表；若带认证则用 basic_auth
    hosts = [url]
    kwargs = {"hosts": hosts}
    if username or password:
        kwargs["basic_auth"] = (username or "", password or "")

    try:
        return AsyncElasticsearch(**kwargs)
    except Exception as e:
        logger.warning(f"构建 ES 客户端失败: {e}")
        return None


async def ensure_es_index(es_config: dict, index_name: str) -> bool:
    """
    若 ES 中不存在该索引则创建（与解析服务索引结构一致）。
    es_config 来自 crud.get_es_config(db)。
    """
    if not index_name or not index_name.strip():
        return False
    index_name = index_name.strip()
    client = _build_es_client(es_config)
    if not client:
        return False
    try:
        exists = await client.indices.exists(index=index_name)
        if exists:
            logger.debug(f"ES 索引已存在: {index_name}")
            return True
        body = {"mappings": ES_INDEX_MAPPINGS, "settings": ES_INDEX_SETTINGS}
        resp = await client.indices.create(index=index_name, **body)
        if resp.get("acknowledged", False):
            logger.info(f"ES 索引已创建: {index_name}")
            return True
        logger.warning(f"创建 ES 索引未确认: {index_name} -> {resp}")
        return False
    except Exception as e:
        logger.error(f"创建 ES 索引失败: index={index_name}, error={e}", exc_info=True)
        return False
    finally:
        await client.close()


async def delete_es_index(es_config: dict, index_name: str) -> bool:
    """
    若 ES 中存在该索引则删除（与创建时 ensure_es_index 对应，backend 直连 ES）。
    es_config 来自 crud.get_es_config(db)。
    """
    if not index_name or not index_name.strip():
        return False
    index_name = index_name.strip()
    client = _build_es_client(es_config)
    if not client:
        return False
    try:
        exists = await client.indices.exists(index=index_name)
        if not exists:
            logger.debug(f"ES 索引不存在，无需删除: {index_name}")
            return True
        resp = await client.indices.delete(index=index_name)
        if resp.get("acknowledged", False):
            logger.info(f"ES 索引已删除: {index_name}")
            return True
        logger.warning(f"删除 ES 索引未确认: {index_name} -> {resp}")
        return False
    except Exception as e:
        logger.error(f"删除 ES 索引失败: index={index_name}, error={e}", exc_info=True)
        return False
    finally:
        await client.close()


async def delete_es_doc_chunks(es_config: dict, index_name: str, doc_id: str) -> bool:
    """
    删除指定文档在 ES 索引中的全部切片（按 doc_id 删除）。
    与解析服务写入结构一致：切片文档含 doc_id 字段（keyword）。
    es_config 来自 crud.get_es_config(db)。
    """
    if not index_name or not index_name.strip():
        return False
    index_name = index_name.strip()
    doc_id = (doc_id or "").strip()
    if not doc_id:
        return False
    client = _build_es_client(es_config)
    if not client:
        return False
    try:
        exists = await client.indices.exists(index=index_name)
        if not exists:
            logger.debug(f"ES 索引不存在，无需删除切片: index={index_name}, doc_id={doc_id}")
            return True
        resp = await client.delete_by_query(
            index=index_name,
            query={"term": {"doc_id": doc_id}},
        )
        deleted = resp.get("deleted", 0)
        if deleted > 0:
            logger.info(f"已删除 ES 中文档切片: index={index_name}, doc_id={doc_id}, deleted={deleted}")
        return True
    except Exception as e:
        logger.error(f"删除 ES 文档切片失败: index={index_name}, doc_id={doc_id}, error={e}", exc_info=True)
        return False
    finally:
        await client.close()
