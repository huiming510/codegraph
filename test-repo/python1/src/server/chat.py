# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/6 11:40
# @Author  : cuils
# @Description:
对话流程接口，多轮的rag
"""
import re
import uuid
import json
from datetime import datetime
from starlette import status
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any, Literal
from fastapi.responses import StreamingResponse
from .container import app_container
from ..memory import DialogEpoch
from ..prompts import (
    REWRITE_QUERY_PROMPT,
    MULTI_TURN_REWRITE_QUERY_PROMPT,
    DIRECT_AUGMENT_GENERATE_PROMPT,
    MULTI_TURN_DIRECT_AUGMENT_GENERATE_PROMPT
)

router = APIRouter(prefix="/chat", tags=["chat"])


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


class ChatRequest(BaseModel):
    session_id: str | None = None
    utterance: str  # 用户输入
    index: str  # 用户要用的知识库
    system_prompt: str | None = None  # 角色/system 提示词，对应助手配置中的「角色」
    search_options: SearchOptions = None
    generate_options: GenerateOptions = None


class ChatResponse(BaseModel):
    status: int = status.HTTP_200_OK
    msg: str | None = None
    session_id: str
    utterance: str
    answer: str | None = None
    references: List[Dict] | None = None


class ChatSSEResponse(BaseModel):
    event: Literal["session_id", "start", "delta", "end", "references", "error", "done"]
    data: str

"""
多轮思路：
每一轮都当作单轮qa实现，
区别在于，从第二轮开始，根据历史query、answer、references生成新的query，然后检索，生成新的答案
问题点：如何总结历史？如何处理references？
"""
async def rewrite_query(query, llm, **kwargs) -> List[str]:
    """query 改写"""
    history_information = kwargs.get("history_information", None)
    if history_information:
        messages = [
            {
                "role": "user",
                "content": MULTI_TURN_REWRITE_QUERY_PROMPT.format(
                    question=query,
                    history_information=history_information
                )
            }
        ]
    else:
        messages = [
            {
                "role": "user",
                "content": REWRITE_QUERY_PROMPT.format(question=query)
            }
        ]
    try:
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
    history_information = kwargs.get("history_information", None)
    total_tokens = await llm.get_tokens_count(prompt=history_information) if history_information else 0
    contents = []
    for i, doc in enumerate(documents):
        content = f"[{i + 1}]:\n{doc['content']}"
        curr_tokens = await llm.get_tokens_count(prompt=content)
        if not curr_tokens:
            curr_tokens = 0
        if total_tokens + curr_tokens > int(llm.max_model_len * 0.8): # 保证还有输出的token，这里上下文最大为模型长度的80%
            break
        contents.append(content)
        total_tokens += curr_tokens

    if history_information:
        messages = [
            {
                "role": "user",
                "content": MULTI_TURN_DIRECT_AUGMENT_GENERATE_PROMPT.format(
                    question=query,
                    history_information=history_information,
                    documents="\n\n".join(contents)
                )
            }
        ]
    else:
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
        if ref_id > len(documents):
            continue
        ref_chunk_id = documents[ref_id - 1]["chunk_id"]
        ref_doc_id = documents[ref_id - 1]["doc_id"]
        content = documents[ref_id - 1]["content"]
        ref_metadata = documents[ref_id - 1]["metadata"]
        references.append(
            {
                "ref_id": ref_id,
                "chunk_id": ref_chunk_id,
                "doc_id": ref_doc_id,
                "content": content,
                "metadata": ref_metadata
            }
        )
    return references


@router.post("/")
async def chat(request: ChatRequest) -> ChatResponse:
    """对话"""
    session_id = request.session_id or str(uuid.uuid4())
    utterance = request.utterance
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

    # 参数验证
    if not utterance or not index:
        return ChatResponse(
            status=status.HTTP_400_BAD_REQUEST,
            msg="No query or index",
            session_id=session_id,
            utterance=utterance
        )

    # 获取当前session对话历史
    history_dialogs: List[DialogEpoch] = await app_container.context_manager.get_history(session_id=session_id)
    history_information = []
    for dialog in history_dialogs:
        dialog_ref_chunks = [f"<ref-{i}>\n{ref}\n</ref-{i}>" for i, ref in enumerate(dialog.ref_chunks, start=1)]
        epoch_info = [
            f"<epoch-{dialog.epoch}>"
            f"<userinput>{dialog.utterance}</userinput>",
            f"<answer>{dialog.response}</answer>",
            f"<search queries>{'; '.join(dialog.search_queries).strip()}</search queries>",
            f"<reference chunks>{'\n'.join(dialog_ref_chunks)}</reference chunks>"
            f"</epoch-{dialog.epoch}>"
        ]
        history_information.append("\n".join(epoch_info))

    # query 改写
    rewrite_queries = await rewrite_query(
        utterance,
        llm,
        temperature=generate_temperature, top_p=generate_top_p,
        history_information=None if not history_information else "\n\n".join(history_information),
    )

    # query检索和重排
    try:
        documents = await multi_query_retrieve(index, rewrite_queries, top_k=search_top_k, method=search_method)
    except Exception as ex:
        return ChatResponse(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            msg=f"检索失败: {ex}",
            session_id=session_id,
            utterance=utterance
        )

    # reranker重排
    documents = await multi_document_rerank(utterance, documents)

    documents = [doc for doc in documents if doc["score"] > search_threshold][:search_top_k]

    # 增强生成
    try:
        answer = await augment_generate(
            utterance,
            documents,
            llm,
            temperature=generate_temperature,
            top_p=generate_top_p,
            history_information=None if not history_information else "\n\n".join(history_information),
        )
    except Exception as ex:
        return ChatResponse(
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            msg=f"生成回复失败: {repr(ex)}",
            session_id=session_id,
            utterance=utterance
        )

    # 识别参考文档
    references = get_references(answer=answer, documents=documents)

    ref_chunks = [ref.pop("content") for ref in references]

    dialog_epoch = DialogEpoch(
        epoch=1 if len(history_dialogs)==0 else history_dialogs[-1].epoch+1,
        utterance=utterance,
        response=answer,
        search_queries=rewrite_queries,
        index=index,
        ref_chunks=ref_chunks,
        search_params=search_options.model_dump(),
        model_params=generate_options.model_dump()
    )

    await app_container.context_manager.set_history(session_id=session_id, dialog_epoch=dialog_epoch)

    return ChatResponse(
        status=status.HTTP_200_OK,
        msg="Success",
        session_id=session_id,
        utterance=utterance,
        answer=answer,
        references=references
    )


def sse_pack(resp: ChatSSEResponse):
    return f"event: {resp.event}\ndata: {resp.data}\n\n"


async def stream_generate(session_id, query, documents, llm, **kwargs) -> List[str]:
    """增强生成"""
    yield sse_pack(ChatSSEResponse(event="session_id", data=session_id))

    history_information = kwargs.get("history_information", None)
    total_tokens = await llm.get_tokens_count(prompt=history_information) if history_information else 0
    contents = []
    for i, doc in enumerate(documents):
        content = f"[{i + 1}]:\n{doc['content']}"
        curr_tokens = await llm.get_tokens_count(prompt=content)
        if not curr_tokens:
            curr_tokens = 0
        if total_tokens + curr_tokens > int(llm.max_model_len * 0.8): # 保证还有输出的token，这里上下文最大为模型长度的80%
            break
        contents.append(content)
        total_tokens += curr_tokens

    # prompt 组装
    if history_information:
        messages = [
            {
                "role": "user",
                "content": MULTI_TURN_DIRECT_AUGMENT_GENERATE_PROMPT.format(
                    question=query,
                    history_information=history_information,
                    documents="\n\n".join(contents)
                )
            }
        ]
    else:
        messages = [
            {
                "role": "user",
                "content": DIRECT_AUGMENT_GENERATE_PROMPT.format(question=query, documents="\n\n".join(contents))
            }
        ]
    system_prompt = kwargs.get("system_prompt")
    if system_prompt:
        messages = [{"role": "system", "content": system_prompt}] + messages

    # 请求llm
    resp = llm.stream_call(
        messages=messages,
        temperature=kwargs.get("generate_options").temperature,
        top_p=kwargs.get("generate_options").top_p
    )

    yield sse_pack(ChatSSEResponse(event="start", data=""))
    buffer = ""
    async for text in resp:
        buffer += text
        yield sse_pack(ChatSSEResponse(event="delta", data=text))

    yield sse_pack(ChatSSEResponse(event="end", data=""))

    # 识别参考文档
    references = get_references(answer=buffer, documents=documents)

    ref_chunks = [ref.pop("content") for ref in references]

    # 更新上下文
    dialog_epoch = DialogEpoch(
        epoch=kwargs.get("epoch"),
        utterance=query,
        response=buffer,
        search_queries=kwargs.get("search_queries"),
        index=kwargs.get("index"),
        ref_chunks=ref_chunks,
        model_params=kwargs.get("generate_options").model_dump(),
        search_params=kwargs.get("search_options").model_dump()
    )

    await app_container.context_manager.set_history(session_id=session_id, dialog_epoch=dialog_epoch)

    yield sse_pack(ChatSSEResponse(event="references", data=json.dumps(references, ensure_ascii=False)))
    yield sse_pack(ChatSSEResponse(event="done", data="[DONE]"))


@router.post("/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    """对话流式返回
    """
    session_id = request.session_id or str(uuid.uuid4())
    utterance = request.utterance
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

    # 参数验证
    if not utterance or not index:
        async def event_gen():
            yield sse_pack(ChatSSEResponse(event="session_id", data=session_id))
            yield sse_pack(ChatSSEResponse(event="start", data=""))
            yield sse_pack(ChatSSEResponse(event="end", data=""))
            yield sse_pack(ChatSSEResponse(event="error", data="No query or index"))
            yield sse_pack(ChatSSEResponse(event="done", data="[DONE]"))

        return StreamingResponse(
            content=event_gen(),
            media_type="text/event-stream"
        )

    # 获取当前session对话历史
    history_dialogs: List[DialogEpoch] = await app_container.context_manager.get_history(session_id=session_id)
    curr_epoch = 1 if not history_dialogs else history_dialogs[-1].epoch+1

    history_information = []
    for dialog in history_dialogs:
        dialog_ref_chunks = [f"<ref-{i}>\n{ref}\n</ref-{i}>" for i, ref in enumerate(dialog.ref_chunks, start=1)]
        epoch_info = [
            f"<epoch-{dialog.epoch}>"
            f"<userinput>{dialog.utterance}</userinput>",
            f"<answer>{dialog.response}</answer>",
            f"<search queries>{'; '.join(dialog.search_queries).strip()}</search queries>",
            f"<reference chunks>{'\n'.join(dialog_ref_chunks)}</reference chunks>"
            f"</epoch-{dialog.epoch}>"
        ]
        history_information.append("\n".join(epoch_info))

    # query 改写
    rewrite_queries = await rewrite_query(
        utterance,
        llm,
        temperature=generate_temperature,
        top_p=generate_top_p,
        history_information=None if not history_information else "\n\n".join(history_information),
    )

    # query检索和重排
    try:
        documents = await multi_query_retrieve(index, rewrite_queries, top_k=search_top_k, method=search_method)
    except Exception as ex:
        async def event_gen(error):
            yield sse_pack(ChatSSEResponse(event="session_id", data=session_id))
            yield sse_pack(ChatSSEResponse(event="start", data=""))
            yield sse_pack(ChatSSEResponse(event="end", data=""))
            yield sse_pack(ChatSSEResponse(event="error", data=error))
            yield sse_pack(ChatSSEResponse(event="done", data="[DONE]"))

        return StreamingResponse(
            content=event_gen(str(ex)),
            media_type="text/event-stream"
        )

    # reranker重排
    documents = await multi_document_rerank(utterance, documents)

    documents = [doc for doc in documents if doc["score"] > search_threshold][:search_top_k]

    return StreamingResponse(
        content=stream_generate(
            session_id=session_id,
            epoch=curr_epoch,
            query=utterance,
            documents=documents,
            llm=llm,
            index=index,
            search_options=search_options,
            generate_options=generate_options,
            search_queries=rewrite_queries,
            history_information="\n\n".join(history_information),
            system_prompt=request.system_prompt,
        ),
        media_type="text/event-stream"
    )



