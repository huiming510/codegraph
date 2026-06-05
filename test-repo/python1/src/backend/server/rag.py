# -*- coding: utf-8 -*-
"""
Backend 侧 RAG 单轮问答：与 src/server/rag.py 流程一致（query 改写 → 检索 → 重排 → 增强生成）。
使用 backend/server/component 的 retriever、reranker、llm（config.yml）。
"""
import asyncio
import re
import uuid
from typing import Tuple, Optional

from .component import retriever, reranker, llm

# 依赖 component 已把 src 加入 path
from prompts import REWRITE_QUERY_PROMPT, DIRECT_AUGMENT_GENERATE_PROMPT


def _call_llm_sync(messages):
    """component.llm 为同步 OpenAIModel，在线程中调用避免阻塞。"""
    return llm(messages=messages)


async def single_turn_rag(
    query: str,
    index: str,
    session_id: Optional[str] = None,
    top_k: int = 20,
    threshold: float = 0.0,
    search_method: str = "dense_filter",
) -> Tuple[str, int, str]:
    """
    单轮 RAG 问答（与 server/rag.py single_turn 一致）。
    返回 (answer, status, msg)，status=200 表示成功，0 表示失败。
    """
    session_id = session_id or str(uuid.uuid4())
    if not query or not index:
        return "", 0, "No query or index"

    # query 改写
    try:
        messages = [{"role": "user", "content": REWRITE_QUERY_PROMPT.format(question=query)}]
        result = await asyncio.to_thread(_call_llm_sync, messages)
        if result:
            rewrite_queries = [q.split(":")[-1].strip() for q in result.strip().split("\n")] + [query]
        else:
            rewrite_queries = [query]
    except Exception:
        rewrite_queries = [query]

    # 检索
    try:
        retrieve_results = await retriever.parallel_retrieve(
            index=index,
            queries=rewrite_queries,
            top_k=top_k,
            method=search_method,
        )
        documents = []
        for retrieve_result in retrieve_results:
            documents.extend(retrieve_result[1])

        chunk_ids = set()
        _res = []
        for chunk in documents:
            if chunk["chunk_id"] in chunk_ids:
                continue
            _res.append(chunk)
            chunk_ids.add(chunk["chunk_id"])
        documents = sorted(_res, key=lambda x: x["score"], reverse=True)
    except Exception as ex:
        return "", 0, f"检索失败: {ex}"

    # reranker 重排
    if reranker:
        try:
            texts = [doc["content"] for doc in documents]
            rerank_scores = await reranker.aencode(query=query, documents=texts)
            for doc, score in zip(documents, rerank_scores):
                doc["score"] = score
            documents = sorted(documents, key=lambda x: x["score"], reverse=True)
        except Exception:
            pass

    documents = [doc for doc in documents if doc["score"] > threshold][:top_k]

    # 增强生成
    try:
        contents = [f"[{i + 1}]:\n{doc['content']}" for i, doc in enumerate(documents)]
        messages = [
            {
                "role": "user",
                "content": DIRECT_AUGMENT_GENERATE_PROMPT.format(
                    question=query, documents="\n\n".join(contents)
                ),
            }
        ]
        answer = await asyncio.to_thread(_call_llm_sync, messages)
    except Exception as ex:
        return "", 0, f"生成回复失败: {repr(ex)}"

    return answer or "", 200, "Success"
