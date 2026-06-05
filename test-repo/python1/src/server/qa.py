# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/28 17:11
# @Author  : cuils
# @Description:
QA流程接口，单轮的rag
"""
import re
import uuid
import json
from starlette import status
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any
from ..prompts import REWRITE_QUERY_PROMPT, DIRECT_AUGMENT_GENERATE_PROMPT
from .container import app_container, rag_logger

router = APIRouter(prefix="/qa", tags=["qa"])


class SearchOptions(BaseModel):
    """搜索相关参数：召回数量、阈值与搜索方式"""
    top_k: int = 20
    threshold: float = 0.
    search_method: str = "dense_filter"


class GenerateOptions(BaseModel):
    """生成相关参数：模型名称、随机性t和topp"""
    model: str = None
    temperature: float = 0.75
    top_p: float = 0.95


class QARequest(BaseModel):
    session_id: str | None = None
    query: str
    index: str
    search_options: SearchOptions = None
    generate_options: GenerateOptions = None


class QAResponse(BaseModel):
    status: int = status.HTTP_200_OK
    msg: str | None = None
    session_id: str
    query: str
    answer: str | None = None
    references: List[Dict] | None = None


async def rewrite_query(query, llm, **kwargs) -> List[str]:
    """query 改写"""
    try:
        messages = [
            {
                "role": "user",
                "content": REWRITE_QUERY_PROMPT.format(question=query)
            }
        ]

        result = await llm(
            messages=messages,
            temperature=kwargs.get("temperature", 0.75),
            top_p=kwargs.get("top_p", 0.95)
        )
        rewrite_queries = [q.split(":")[-1].strip() for q in result.strip().split("\n")] + [query]
    except:
        rewrite_queries = [query]
    return rewrite_queries


async def multi_query_retrieve(index, queries, **kwargs) -> List[Any]:
    """检索"""
    retrieve_results = await app_container.retriever.parallel_retrieve(
        index=index,
        queries=queries,
        top_k=kwargs.get("top_k", 20),
        method=kwargs.get("method", "dense"),
    )

    documents = []
    max_elapsed = 0
    for retrieve_result in retrieve_results:
        documents.extend(retrieve_result[1])
        max_elapsed = max(max_elapsed, retrieve_result[0])

    chunk_ids = set()
    _res = []
    for chunk in documents:
        if chunk["chunk_id"] in chunk_ids:
            continue
        _res.append(chunk)
        chunk_ids.add(chunk["chunk_id"])

    # 仅相似度重排
    documents = sorted(_res, key=lambda x: x["score"], reverse=True)
    return documents


async def multi_document_rerank(query, documents) -> List[Any]:
    """多文档重排"""
    if app_container.reranker_model:
        try:
            texts = [doc["content"] for doc in documents]
            rerank_scores = await app_container.reranker_model.aencode(query=query, documents=texts)
            for doc, score in zip(documents, rerank_scores):
                doc["score"] = score

            documents = sorted(documents, key=lambda x: x["score"], reverse=True)
        except Exception:
            pass
    return documents


async def augment_generate(query, documents, llm, **kwargs) -> List[str]:
    """增强生成"""
    # 增强生成
    total_tokens = 0
    contents = []
    for i, doc in enumerate(documents):
        content = f"[{i + 1}]:\n{doc['content']}"
        curr_tokens = await llm.get_tokens_count(prompt=content)
        if not curr_tokens:
            curr_tokens = 4096
        if total_tokens + curr_tokens > llm.max_model_len:
            break
        contents.append(content)
        total_tokens += curr_tokens

    messages = [
        {
            "role": "user",
            "content": DIRECT_AUGMENT_GENERATE_PROMPT.format(question=query, documents="\n\n".join(contents))
        }
    ]

    answer = await llm(
        messages=messages,
        temperature=kwargs.get("temperature", 0.75),
        top_p=kwargs.get("top_p", 0.95)
    )
    return answer


def get_references(answer, documents) -> List[Dict]:
    """获取参考文档信息"""
    ref_ids = re.findall(r"\[(\d+)\]", answer)  # noqa
    ref_ids = sorted(list(map(int, list(set(ref_ids)))))
    references = []
    for ref_id in ref_ids:
        if ref_id <= 0 or ref_id > len(documents):
            continue
        ref_chunk_id = documents[ref_id - 1]["chunk_id"]
        ref_doc_id = documents[ref_id - 1]["doc_id"]
        ref_metadata = documents[ref_id - 1]["metadata"]
        references.append(
            {
                "chunk_id": ref_chunk_id,
                "doc_id": ref_doc_id,
                "metadata": ref_metadata
            }
        )
    return references


@router.post("/")
async def qa_flow(request: QARequest):
    """单轮搜索问答，不支持追问"""
    session_id = request.session_id or str(uuid.uuid4())
    query = request.query
    index = request.index

    # 搜索参数
    search_options = request.search_options or SearchOptions()
    search_top_k = search_options.top_k
    search_threshold = search_options.threshold
    search_method = search_options.search_method

    # 生成参数
    generate_options = request.generate_options or GenerateOptions()
    generate_model = generate_options.model
    generate_temperature = generate_options.temperature
    generate_top_p = generate_options.top_p

    if generate_model in app_container.llm_models:
        llm = app_container.llm_models[generate_model]
    else:
        llm = list(app_container.llm_models.values())[0]

    _log = {
        "session_id": session_id,
        "status": 200,
        "request": request.model_dump(),
        "response": None,
        "extra": {}
    }

    # 参数验证
    if not query or not index:
        resp = QAResponse(
            status=status.HTTP_400_BAD_REQUEST,
            msg="No query or index",
            session_id=session_id,
            query=query
        )
        _log["status"] = 0
        _log["response"] = resp.model_dump()
        rag_logger.info(json.dumps(_log, ensure_ascii=False))
        return resp

    # query 改写
    rewrite_queries = await rewrite_query(query, llm, temperature=generate_temperature, top_p=generate_top_p)

    _log["extra"]["rewrite_queries"] = rewrite_queries

    # query检索和重排
    try:
        documents = await multi_query_retrieve(index, rewrite_queries, top_k=search_top_k, method=search_method)
    except Exception as ex:
        resp = QAResponse(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            msg=f"检索失败: {ex}",
            session_id=session_id,
            query=query
        )
        _log["status"] = 0
        _log["response"] = resp.model_dump()
        rag_logger.info(json.dumps(_log, ensure_ascii=False))
        return resp

    # reranker重排
    documents = await multi_document_rerank(query, documents)

    documents = [doc for doc in documents if doc["score"] > search_threshold][:search_top_k]

    _log["extra"]["documents"] = [
        {"chunk_id": doc["chunk_id"], "score": doc["score"], "metadata": doc["metadata"]}
        for doc in documents
    ]

    # 增强生成
    try:
        answer = await augment_generate(query, documents, llm, temperature=generate_temperature, top_p=generate_top_p)
    except Exception as ex:
        resp = QAResponse(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            msg=f"生成回复失败: {repr(ex)}",
            session_id=session_id,
            query=query
        )
        _log["status"] = 0
        _log["response"] = resp.model_dump()
        rag_logger.info(json.dumps(_log, ensure_ascii=False))
        return resp

    # 识别参考文档
    references = get_references(answer=answer, documents=documents)

    resp = QAResponse(
        status=status.HTTP_200_OK,
        msg="Success",
        session_id=session_id,
        query=query,
        answer=answer,
        references=references
    )
    _log["response"] = resp.model_dump()
    rag_logger.info(json.dumps(_log, ensure_ascii=False))
    return resp