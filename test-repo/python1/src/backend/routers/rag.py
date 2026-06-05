"""RAG：查询、对话、流式对话、历史、会话列表。对话采用 server/rag 单轮 RAG 发问回答。"""
import asyncio
import json
import re
import time
import traceback
from typing import Optional, Tuple, List, Any
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db, crud
from llm.base import Message
from logger import logger
from server.client import LinkragServerClient
from .common import success_response
from .deps import get_current_user

router = APIRouter(prefix="/api", tags=["RAG"])


def _get_qa_service_url() -> str:
    """获取 QA 流程服务地址"""
    url = (settings.qa_service_url or settings.linkrag_server_url or "").rstrip("/")
    if not url:
        raise ValueError("未配置 qa_service_url 或 linkrag_server_url，无法调用 QA 流程")
    return url


# 模型默认值
DEFAULT_LLM_ID = "Qwen3-30B-A3B-Instruct-2507"

# server/rag 单轮问答默认 top_k
CHAT_RAG_TOP_K = 20

# 由 main 注入
_llm = None


def _parse_references_from_content(content: str) -> Tuple[str, List[dict]]:
    """
    从内容中解析并剥离「参考片段：...」部分。
    外部 API 可能将 references 以「参考片段：[1][2][3][{...}]」形式追加到正文末尾。
    返回 (清理后的正文, references 列表)。
    """
    if not content or "参考片段" not in content:
        return content, []
    idx = content.find("参考片段")
    if idx == -1:
        return content, []
    # 找到 JSON 数组起始 [{
    ref_part = content[idx:]
    start = ref_part.find("[{")
    if start == -1:
        return content[:idx].rstrip(), []
    # 匹配到对应的 ]
    depth = 0
    end_in_ref = -1
    for i in range(start, len(ref_part)):
        c = ref_part[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                end_in_ref = i
                break
    if end_in_ref == -1:
        return content[:idx].rstrip(), []
    try:
        refs = json.loads(ref_part[start : end_in_ref + 1])
        refs = refs if isinstance(refs, list) else []
    except (json.JSONDecodeError, TypeError):
        refs = []
    return content[:idx].rstrip(), refs


def _strip_session_id_from_content(content: str, session_id: str = None) -> str:
    """
    通过替换移除内容中外部 API 可能带入的 session_id，避免历史回答中显示会话 ID。
    """
    if not content:
        return content
    if session_id:
        content = content.replace(session_id, "").strip()
    return content


def _is_connection_error(e: Exception) -> bool:
    """判断是否为连接类错误（无法到达目标服务器，如 192.168.10.187:8000）"""
    msg = str(e).lower()
    return any(
        k in msg
        for k in ("connect", "connection", "refused", "timeout", "unreachable", "network")
    )


def _stream_error(msg: str):
    """将错误信息以 SSE delta 形式输出，便于前端展示为消息内容"""
    yield f"event: delta\ndata: {msg}\n\n"
    yield "data: [DONE]\n\n"


def set_llm(llm):
    global _llm
    _llm = llm


def get_llm_instance():
    if _llm is None:
        raise RuntimeError("LLM not initialized")
    return _llm


# 知识库内容（与 main 中保持一致，后续可从数据库读取）
knowledge_base = {
    "Python": "Python是一种解释型、面向对象、动态数据类型的高级程序设计语言。",
    "机器学习": "机器学习是人工智能的一个分支，它使计算机系统能够从数据中学习并改进。",
    "FastAPI": "FastAPI是一个用于构建API的现代、快速的Web框架，基于Python 3.6+的类型提示。",
    "Vue3": "Vue3是Vue.js的最新主要版本，引入了Composition API、更好的TypeScript支持。",
    "RAG": "RAG（Retrieval-Augmented Generation）是一种结合检索和生成的AI技术。",
}


class QuerySearchOptions(BaseModel):
    """查询搜索参数（前台传入）"""
    top_k: int = 20
    threshold: float = 0.0
    search_method: str = "dense"


class QueryGenerateOptions(BaseModel):
    """查询生成参数（前台传入）"""
    model: Optional[str] = None
    temperature: float = 0.75
    top_p: float = 0.95


class QueryRequest(BaseModel):
    query: str
    knowledge_base_id: Optional[int] = None
    top_k: Optional[int] = 3
    search_app_id: Optional[int] = None  # 搜索应用ID，用于获取配置
    language: Optional[str] = "zh"  # 语言设置
    system_prompt: Optional[str] = None  # 系统提示词
    search_options: Optional[QuerySearchOptions] = None
    generate_options: Optional[QueryGenerateOptions] = None


class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    knowledge_base_id: Optional[int] = None


class ChatStreamProxyRequest(BaseModel):
    """流式对话代理请求，转发到外部多轮对话 API"""
    session_id: str
    utterance: str
    index: str
    app_session_key: Optional[str] = None  # 助手 key，用于会话不存在时创建并关联
    system_prompt: Optional[str] = None  # 角色/system 提示词，对应助手配置中的「角色」
    search_options: Optional[dict] = None
    generate_options: Optional[dict] = None


class SaveQueryResultRequest(BaseModel):
    """保存查询结果请求"""
    query: str
    answer: str
    sources: List[dict]  # [{"document_id": int, "filename": str, "file_path": str, "relevance": float}]
    knowledge_base_id: int
    search_app_id: Optional[int] = None
    top_k: int = 3
    llm_id: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    search_method: Optional[str] = None
    similarity_threshold: Optional[float] = None


class QAFlowSearchOptions(BaseModel):
    """QA 流程搜索参数"""
    top_k: int = 20
    threshold: float = 0.0
    search_method: str = "dense"


class QAFlowGenerateOptions(BaseModel):
    """QA 流程生成参数"""
    model: Optional[str] = None
    temperature: float = 0.1
    top_p: float = 0.3


class QAFlowRequest(BaseModel):
    """QA 流程代理请求（对应 POST /qa/ 接口）"""
    query: str
    knowledge_base_id: Optional[int] = None
    search_app_id: Optional[int] = None
    search_options: Optional[QAFlowSearchOptions] = None
    generate_options: Optional[QAFlowGenerateOptions] = None


class SearchAppCreate(BaseModel):
    """搜索应用创建/更新；参数配置简化为：模型、temperature、top_p、检索方式、top_k、threshold"""
    name: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    kb_ids: list[int] = []
    similarity_threshold: float = 0.2
    vector_similarity_weight: float = 0.3
    rerank_id: Optional[str] = None
    use_rerank: bool = False
    top_k: int = 20
    summary: bool = False
    llm_id: Optional[str] = DEFAULT_LLM_ID
    temperature: float = 0.1
    top_p: float = 0.3
    presence_penalty: float = 0.4
    frequency_penalty: float = 0.7
    related_search: bool = False
    query_mindmap: bool = False
    search_method: Optional[str] = "dense"


class ChatAppCreate(BaseModel):
    """聊天应用创建"""
    name: str
    icon: Optional[str] = None
    description: Optional[str] = None
    prologue: Optional[str] = None
    empty_response: Optional[str] = None
    kb_ids: list[int] = []
    quote: bool = True
    keyword: bool = False
    tts: bool = False
    similarity_threshold: float = 0.2
    vector_similarity_weight: float = 0.3
    top_n: int = 8
    llm_id: Optional[str] = None
    temperature: float = 0.1
    top_p: float = 0.3
    search_options: Optional[dict] = None
    generate_options: Optional[dict] = None


class ChatAppConfigUpdate(BaseModel):
    """聊天应用对话配置更新（description、search_options、generate_options）"""
    description: Optional[str] = None
    search_options: Optional[dict] = None
    generate_options: Optional[dict] = None


class SessionTitleUpdate(BaseModel):
    """会话/对话标题更新"""
    title: str


async def _references_to_sources(references: list, db: AsyncSession) -> list:
    """将 QA 返回的 references 转为前端 sources 格式，根据 document_id 查询数据库获取文件名和路径"""
    if not references:
        return []
    result = []
    for i, ref in enumerate(references):
        try:
            document_id = int(ref.get("doc_id", 0))
        except (ValueError, TypeError):
            document_id = 0

        meta = ref.get("metadata") or {}
        filename = meta.get("filename", f"文档{document_id}")
        file_path = meta.get("file_path", "")

        if document_id > 0:
            try:
                document = await crud.get_document_by_id(db, document_id)
                if document:
                    filename = document.filename
                    file_path = document.file_path
            except Exception as e:
                logger.warning(f"查询文档信息失败 document_id={document_id}: {e}")

        result.append({
            "document_id": document_id,
            "filename": filename,
            "file_path": file_path,
            "content_snippet": meta.get("content", meta.get("content_snippet", "")),
            "relevance": meta.get("score", 1.0 - i * 0.05),
        })
    return result


@router.post("/query")
async def query_rag_stream(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """RAG 查询接口 - 调用 QA 服务并模拟流式输出"""
    async def generate():
        try:
            base_url = _get_qa_service_url()
            qa_url = f"{base_url}/qa/"

            kb_id = request.knowledge_base_id
            if not kb_id and request.search_app_id:
                app = await crud.get_search_app_by_id(db, request.search_app_id)
                if app and app.kb_ids:
                    kb_id = app.kb_ids[0] if isinstance(app.kb_ids, list) else app.kb_ids[0]

            if not kb_id:
                yield f"data: {json.dumps({'type': 'error', 'content': '未指定知识库'})}\n\n"
                return

            kb = await crud.get_knowledge_base(db, kb_id)
            if not kb:
                yield f"data: {json.dumps({'type': 'error', 'content': '知识库不存在'})}\n\n"
                return

            index_name = LinkragServerClient.resolve_kb_index_name(kb)

            if request.search_options:
                search_opts = request.search_options.model_dump()
            elif request.search_app_id:
                app = await crud.get_search_app_by_id(db, request.search_app_id)
                if app:
                    search_opts = {
                        "top_k": app.top_k,
                        "threshold": app.similarity_threshold,
                        "search_method": app.search_method or "dense",
                    }
                else:
                    search_opts = {"top_k": request.top_k or 20, "threshold": 0.0, "search_method": "dense"}
            else:
                search_opts = {"top_k": request.top_k or 20, "threshold": 0.0, "search_method": "dense"}

            if request.generate_options:
                gen_opts = request.generate_options.model_dump()
                if gen_opts.get("model") is None:
                    gen_opts["model"] = DEFAULT_LLM_ID
            elif request.search_app_id:
                app = await crud.get_search_app_by_id(db, request.search_app_id)
                if app:
                    gen_opts = {
                        "model": app.llm_id or DEFAULT_LLM_ID,
                        "temperature": app.temperature,
                        "top_p": app.top_p,
                    }
                else:
                    gen_opts = {"model": DEFAULT_LLM_ID, "temperature": 0.75, "top_p": 0.95}
            else:
                gen_opts = {"model": DEFAULT_LLM_ID, "temperature": 0.75, "top_p": 0.95}

            payload = {
                "session_id": f"query_{request.search_app_id or kb_id}_{int(time.time())}",
                "query": request.query,
                "index": index_name,
                "language": request.language,
                "system_prompt": request.system_prompt,
                **search_opts,
                **gen_opts,
            }

            logger.info(f"调用QA服务前payload: {json.dumps(payload, ensure_ascii=False)}")

            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                resp = await client.post(qa_url, json=payload)

            if resp.status_code != 200:
                error_detail = f"QA 服务调用失败 (状态码: {resp.status_code})"
                try:
                    error_data = resp.json()
                    if error_data.get("msg"):
                        error_detail += f": {error_data['msg']}"
                except Exception:
                    pass
                logger.error(f"QA 服务调用失败: {error_detail}")
                yield f"data: {json.dumps({'type': 'error', 'content': error_detail})}\n\n"
                return

            result = resp.json()

            if result.get("status") != 200:
                error_msg = result.get("msg", "QA 流程返回错误")
                logger.error(f"QA 流程错误: {error_msg}")
                yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'thinking', 'content': '正在分析问题...'})}\n\n"
            await asyncio.sleep(0.5)

            references = result.get("references") or []
            sources = await _references_to_sources(references, db)
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
            await asyncio.sleep(0.3)

            answer = result.get("answer", "")

            if answer:
                # 按空白符切分但保留空白（含换行），保证 Markdown 表格等格式正确展示
                tokens = re.split(r"(\s+)", answer)
                for token in tokens:
                    if token:
                        yield f"data: {json.dumps({'type': 'answer', 'answer': token, 'is_complete': False})}\n\n"
                        await asyncio.sleep(0.02)
                yield f"data: {json.dumps({'type': 'answer', 'answer': '', 'is_complete': True})}\n\n"

            yield f"data: {json.dumps({'type': 'complete', 'session_id': payload['session_id']})}\n\n"

        except httpx.TimeoutException:
            logger.error("QA 服务请求超时")
            yield f"data: {json.dumps({'type': 'error', 'content': 'QA 服务请求超时，请稍后重试'})}\n\n"
        except httpx.ConnectError:
            logger.error("无法连接到 QA 服务")
            yield f"data: {json.dumps({'type': 'error', 'content': '无法连接到 QA 服务，请检查服务是否运行'})}\n\n"
        except Exception as e:
            logger.error(f"查询流式转发失败: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': f'查询失败: {str(e)}'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/save-query-result")
async def save_query_result(
    request: SaveQueryResultRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """保存查询结果到数据库"""
    try:
        start_time = time.time()

        kb = await crud.get_knowledge_base(db, request.knowledge_base_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")

        latency_ms = int((time.time() - start_time) * 1000)

        model_config = {}
        if request.llm_id:
            model_config['llm_id'] = request.llm_id
        if request.temperature is not None:
            model_config['temperature'] = request.temperature
        if request.top_p is not None:
            model_config['top_p'] = request.top_p
        if request.search_method:
            model_config['search_method'] = request.search_method
        if request.similarity_threshold is not None:
            model_config['similarity_threshold'] = request.similarity_threshold

        query_log = await crud.create_query_log(
            db=db,
            query=request.query,
            answer=request.answer,
            sources=request.sources,
            top_k=request.top_k,
            knowledge_base_id=request.knowledge_base_id,
            search_app_id=request.search_app_id,
            model=request.llm_id,
            user_id=str(current_user.id) if current_user else None,
            latency_ms=latency_ms,
            ip_address=http_request.client.host if http_request.client else None,
            success=True,
            model_config=model_config if model_config else None,
        )

        await db.commit()

        logger.info(f"查询结果已保存 | 问题: {request.query[:50]}... | 耗时: {latency_ms}ms | 文档数: {len(request.sources)}")

        return success_response(data={"query_log_id": query_log.id})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"保存查询结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qa-flow")
async def qa_flow_proxy(
    request: QAFlowRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """代理调用 QA 流程接口（POST /qa/）。将 knowledge_base_id / search_app_id 解析为 index，转发到 linkrag QA 服务。"""
    try:
        base_url = _get_qa_service_url()
        qa_url = f"{base_url}/qa/"

        kb_id = request.knowledge_base_id
        if not kb_id and request.search_app_id:
            app = await crud.get_search_app_by_id(db, request.search_app_id)
            if app and app.kb_ids:
                kb_id = app.kb_ids[0] if isinstance(app.kb_ids, list) else app.kb_ids[0]

        if not kb_id:
            raise HTTPException(status_code=400, detail="未指定知识库")

        kb = await crud.get_knowledge_base(db, kb_id)
        if not kb:
            raise HTTPException(status_code=404, detail="知识库不存在")

        index_name = LinkragServerClient.resolve_kb_index_name(kb)

        search_opts = request.search_options or QAFlowSearchOptions()
        gen_opts = request.generate_options or QAFlowGenerateOptions()

        if request.search_app_id:
            app = await crud.get_search_app_by_id(db, request.search_app_id)
            if app:
                search_opts = QAFlowSearchOptions(
                    top_k=app.top_k,
                    threshold=app.similarity_threshold,
                    search_method=app.search_method or "dense"
                )
                gen_opts = QAFlowGenerateOptions(
                    model=app.llm_id or DEFAULT_LLM_ID,
                    temperature=app.temperature,
                    top_p=app.top_p
                )

        payload: dict[str, Any] = {
            "query": request.query,
            "index": index_name,
            "search_options": {
                "top_k": search_opts.top_k,
                "threshold": search_opts.threshold,
                "search_method": search_opts.search_method
            },
            "generate_options": {
                "model": gen_opts.model,
                "temperature": gen_opts.temperature,
                "top_p": gen_opts.top_p
            }
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(qa_url, json=payload)

        result = resp.json()

        if resp.status_code != 200:
            msg = result.get("msg", "QA 服务调用失败")
            raise HTTPException(status_code=resp.status_code, detail=msg)

        if result.get("status") != 200:
            raise HTTPException(
                status_code=500,
                detail=result.get("msg", "QA 流程返回错误")
            )

        return success_response(data={
            "session_id": result.get("session_id"),
            "query": result.get("query"),
            "answer": result.get("answer"),
            "references": result.get("references") or []
        })
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"QA 流程代理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Chat 对话接口"""
    llm = get_llm_instance()
    start_time = time.time()
    try:
        session_key = request.session_id or f"session_{int(time.time() * 1000)}"
        session = await crud.get_session(db, session_key)
        if not session:
            user_id = current_user.id if current_user else None
            session = await crud.create_session(db, session_key, user_id=user_id)
            logger.info(f"创建新会话: {session_key} | 用户: {current_user.username if current_user else '匿名'}")

        await crud.create_message(
            db=db,
            session_id=session.id,
            role="user",
            content=request.message,
        )

        # 采用 server/rag 单轮 RAG 发问回答（需选择知识库）
        if request.knowledge_base_id:
            from server.rag import single_turn_rag as server_single_turn_rag
            kb = await crud.get_knowledge_base(db, request.knowledge_base_id)
            if not kb:
                raise HTTPException(status_code=400, detail="知识库不存在")
            index_name = LinkragServerClient.resolve_kb_index_name(kb)
            answer, status, msg = await server_single_turn_rag(
                query=request.message,
                index=index_name,
                session_id=session_key,
                top_k=CHAT_RAG_TOP_K,
                threshold=0.0,
                search_method="dense_filter",
            )
            if status != 200:
                raise HTTPException(status_code=500, detail=msg or "RAG 回答失败")
            ai_content = answer or ""
        else:
            # 未选知识库时走原 LLM 对话
            history = await crud.get_session_messages(db, session.id, limit=10)
            messages = [Message(role="system", content="你是一个基于知识库的AI助手，请友好地回答用户问题。")]
            for msg in history:
                messages.append(Message(role=msg.role, content=msg.content))
            response = await llm.chat(messages)
            ai_content = response.content

        latency_ms = int((time.time() - start_time) * 1000)
        await crud.create_message(
            db=db,
            session_id=session.id,
            role="assistant",
            content=ai_content,
            tokens_used=0,
            model=getattr(llm, "config", None) and getattr(llm.config, "model", None) or None,
            latency_ms=latency_ms,
        )
        if session.title == "新对话":
            title = request.message[:20] + ("..." if len(request.message) > 20 else "")
            await crud.update_session(db, session_key, title=title)

        logger.info(f"对话完成 | 会话: {session_key} | 耗时: {latency_ms}ms")

        return success_response(data={"response": ai_content, "session_id": session_key})
    except Exception as e:
        logger.error(f"对话失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream-external")
async def chat_stream_external(
    request: ChatStreamProxyRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    多轮流式对话代理：转发到外部 /chat/stream，实现多轮对话。
    请求体格式与外部 API 一致：session_id, utterance, index, search_options, generate_options。
    用户消息与助手回复会持久化到 chat_messages 表，便于点击对话时加载历史。
    """
    base_url = (settings.chat_stream_url or "http://192.168.10.187:8000").rstrip("/")
    url = f"{base_url}/chat/stream"
    body = {
        "session_id": request.session_id,
        "utterance": request.utterance,
        "index": request.index,
        "search_options": request.search_options or {"search_method": "dense"},
        "generate_options": request.generate_options or {"model": "Qwen3-30B-A3B-Instrunct-2507"},
    }
    if request.system_prompt:
        body["system_prompt"] = request.system_prompt

    # 1. 获取或创建会话，并持久化用户消息
    session = await crud.get_session(db, request.session_id)
    if not session and request.app_session_key:
        # 会话不存在时创建（兼容外部 API 或历史流程创建的 session_id）
        app_session = await crud.get_session(db, request.app_session_key)
        if app_session and app_session.session_key.startswith("app_") and not app_session.parent_session_key:
            user_id = current_user.id if current_user else None
            await crud.create_session(
                db=db,
                session_key=request.session_id,
                title="新对话",
                user_id=user_id,
                parent_session_key=request.app_session_key,
            )
            await db.commit()
            session = await crud.get_session(db, request.session_id)
    session_id_for_save = None
    if session:
        await crud.create_message(
            db=db,
            session_id=session.id,
            role="user",
            content=request.utterance,
        )
        session_id_for_save = session.id
        await db.commit()

    async def generate():
        full_response = ""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, json=body) as resp:
                    if resp.status_code != 200:
                        err = await resp.aread()
                        logger.error(f"流式对话代理失败: {resp.status_code} {err[:200]}")
                        for chunk in _stream_error("服务器连接失败，请联系管理员！"):
                            yield chunk
                        return
                    async for chunk in resp.aiter_text():
                        full_response += chunk
                        yield chunk
        except Exception as e:
            logger.error(f"流式对话代理异常: {e}")
            err_msg = "服务器连接失败，请联系管理员！" if _is_connection_error(e) else f"请求异常: {e}"
            for chunk in _stream_error(err_msg):
                yield chunk
        finally:
            # 2. 流结束后解析 SSE：提取 delta 内容与 references，持久化助手回复（保留原样式所需数据）
            if session_id_for_save:
                content_parts = []
                references = []
                current_event = ""
                for line in full_response.split("\n"):
                    if line.startswith("event: "):
                        current_event = line[7:].strip()
                    elif line.startswith("data: "):
                        d = line[6:]
                        if d == "[DONE]":
                            continue
                        if current_event == "delta":
                            content_parts.append(d)
                        elif current_event == "references":
                            try:
                                refs = json.loads(d)
                                references = refs if isinstance(refs, list) else []
                            except (json.JSONDecodeError, TypeError):
                                references = []
                ai_content_raw = "".join(content_parts) if content_parts else "（暂无回复）"
                # 从正文解析并剥离「参考片段：...」部分（外部 API 可能将 refs 以该形式追加到正文末尾）
                ai_content, refs_from_content = _parse_references_from_content(ai_content_raw)
                references = references if references else refs_from_content
                # 通过替换移除外部 API 可能带入的 session_id，避免历史回答中显示会话 ID
                ai_content = _strip_session_id_from_content(ai_content, request.session_id)
                extra_data = {"references": references} if references else None
                from database.connection import AsyncSessionLocal
                async with AsyncSessionLocal() as db_save:
                    await crud.create_message(
                        db=db_save,
                        session_id=session_id_for_save,
                        role="assistant",
                        content=ai_content,
                        extra_data=extra_data,
                    )
                    await crud.update_session(db_save, request.session_id)
                    await db_save.commit()

    return StreamingResponse(generate(), media_type="text/event-stream; charset=utf-8")


@router.post("/chat/stream")
async def chat_stream(
    request: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """流式 Chat 对话接口；选知识库时走 server/rag 单轮 RAG，结果整段以流式输出。"""
    llm = get_llm_instance()
    session_key = request.session_id or f"session_{int(time.time() * 1000)}"
    session = await crud.get_session(db, session_key)
    if not session:
        session = await crud.create_session(db, session_key)

    await crud.create_message(db=db, session_id=session.id, role="user", content=request.message)

    async def generate():
        from database.connection import AsyncSessionLocal
        full_response = ""
        start_time = time.time()
        if request.knowledge_base_id:
            from server.rag import single_turn_rag as server_single_turn_rag
            async with AsyncSessionLocal() as db_stream:
                kb = await crud.get_knowledge_base(db_stream, request.knowledge_base_id)
            if kb:
                index_name = LinkragServerClient.resolve_kb_index_name(kb)
                answer, status, _ = await server_single_turn_rag(
                    query=request.message,
                    index=index_name,
                    session_id=session_key,
                    top_k=CHAT_RAG_TOP_K,
                    threshold=0.0,
                    search_method="dense_filter",
                )
                if status == 200 and answer:
                    full_response = answer
                    for ch in answer:
                        yield f"data: {ch}\n\n"
            if not full_response:
                full_response = "（未选择有效知识库或 RAG 未返回结果）"
                yield f"data: {full_response}\n\n"
        else:
            async with AsyncSessionLocal() as db_stream:
                history = await crud.get_session_messages(db_stream, session.id, limit=10)
            messages = [Message(role="system", content="你是一个基于知识库的AI助手，请友好地回答用户问题。")]
            for msg in history:
                messages.append(Message(role=msg.role, content=msg.content))
            async for chunk in llm.chat_stream(messages):
                full_response += chunk
                yield f"data: {chunk}\n\n"

        latency_ms = int((time.time() - start_time) * 1000)
        from database.connection import AsyncSessionLocal
        async with AsyncSessionLocal() as db_session:
            await crud.create_message(
                db=db_session,
                session_id=session.id,
                role="assistant",
                content=full_response,
                latency_ms=latency_ms,
            )
            await db_session.commit()

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取对话历史；仅返回当前用户归属的会话消息，确保点击显示自己的对话历史"""
    session = await crud.get_session(db, session_id)
    if not session:
        return success_response(data={"messages": []})
    # 仅返回当前用户自己的会话（user_id 一致或未登录时仅允许 user_id 为空的会话）
    if current_user and session.user_id is not None and session.user_id != current_user.id:
        return success_response(data={"messages": []})
    if not current_user and session.user_id is not None:
        return success_response(data={"messages": []})

    messages = await crud.get_session_messages(db, session.id, limit=50)
    result = []
    for msg in messages:
        refs = (msg.extra_data or {}).get("references", [])
        content = msg.content
        # 兼容旧数据：若 extra_data 无 references 但正文含「参考片段：...」，解析并剥离
        if not refs and msg.role == "assistant":
            content, refs = _parse_references_from_content(content)
        # 通过替换移除外部 API 可能带入的 session_id，避免历史回答中显示会话 ID
        content = _strip_session_id_from_content(content, session_id)
        result.append({
            "role": msg.role,
            "content": content,
            "timestamp": msg.created_at.isoformat(),
            "references": refs,
        })
    return success_response(data={"messages": result})


@router.put("/chat/sessions/{session_key}")
async def update_session_title(
    session_key: str,
    body: SessionTitleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新会话/对话标题（用于首条消息后更新对话标题）"""
    session = await crud.get_session(db, session_key)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    await crud.update_session(db, session_key, title=body.title[:200])
    await db.commit()
    return success_response(data={"session_key": session_key, "title": body.title})


@router.get("/chat/sessions")
async def get_user_sessions(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取用户的会话列表"""
    if not current_user:
        return success_response(data={"sessions": []})

    sessions = await crud.get_user_sessions(db, current_user.id, limit=50)
    return success_response(
        data={
            "sessions": [
                {
                    "key": s.session_key,
                    "title": s.title,
                    "message_count": s.message_count,
                    "updated_at": s.updated_at.isoformat(),
                }
                for s in sessions
            ]
        }
    )


# ==================== 搜索应用管理 ====================

@router.post("/search-apps")
async def create_search_app(
    app: SearchAppCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建搜索应用"""
    try:
        search_app = await crud.create_search_app(
            db=db,
            name=app.name,
            description=app.description,
            avatar=app.avatar,
            kb_ids=app.kb_ids,
            similarity_threshold=app.similarity_threshold,
            vector_similarity_weight=app.vector_similarity_weight,
            rerank_id=app.rerank_id,
            use_rerank=app.use_rerank,
            top_k=app.top_k,
            summary=app.summary,
            llm_id=app.llm_id or DEFAULT_LLM_ID,
            temperature=app.temperature,
            top_p=app.top_p,
            presence_penalty=app.presence_penalty,
            frequency_penalty=app.frequency_penalty,
            related_search=app.related_search,
            query_mindmap=app.query_mindmap,
            search_method=app.search_method or "dense",
            creator_id=current_user.id if current_user else None,
        )
        await db.commit()
        logger.info(f"创建搜索应用: {app.name} | 用户: {current_user.username if current_user else '匿名'}")
        return success_response(data={"id": search_app.id, "name": app.name})
    except Exception as e:
        logger.error(f"创建搜索应用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-apps")
async def get_search_apps(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取搜索应用列表"""
    try:
        apps_list = await crud.get_search_apps(db, limit=100, creator_id=current_user.id if current_user else None)
        result = []
        for app in apps_list:
            result.append({
                "id": app.id,
                "name": app.name,
                "description": app.description or "",
                "avatar": app.avatar or "",
                "kb_ids": app.kb_ids or [],
                "similarity_threshold": app.similarity_threshold,
                "top_k": app.top_k,
                "llm_id": app.llm_id or DEFAULT_LLM_ID,
                "temperature": app.temperature,
                "top_p": app.top_p,
                "search_method": app.search_method or "dense",
                "created_at": app.created_at.isoformat(),
            })
        return success_response(data={"apps": result})
    except Exception as e:
        logger.error(f"获取搜索应用列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-apps/{app_id}")
async def get_search_app(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取单个搜索应用详情"""
    try:
        app = await crud.get_search_app_by_id(db, app_id)
        if not app:
            raise HTTPException(status_code=404, detail="检索不存在")

        if app.creator_id and current_user and app.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权限访问此检索")

        result = {
            "id": app.id,
            "name": app.name,
            "description": app.description or "",
            "avatar": app.avatar or "",
            "kb_ids": app.kb_ids or [],
            "similarity_threshold": app.similarity_threshold,
            "vector_similarity_weight": app.vector_similarity_weight,
            "rerank_id": app.rerank_id or "",
            "use_rerank": app.use_rerank,
            "top_k": app.top_k,
            "summary": app.summary,
            "llm_id": app.llm_id or DEFAULT_LLM_ID,
            "temperature": app.temperature,
            "top_p": app.top_p,
            "presence_penalty": app.presence_penalty,
            "frequency_penalty": app.frequency_penalty,
            "related_search": app.related_search,
            "query_mindmap": app.query_mindmap,
            "search_method": app.search_method or "dense",
            "created_at": app.created_at.isoformat(),
        }
        return success_response(data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取搜索应用详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/search-apps/{app_id}")
async def update_search_app(
    app_id: int,
    app: SearchAppCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新搜索应用"""
    try:
        existing_app = await crud.get_search_app_by_id(db, app_id)
        if not existing_app:
            raise HTTPException(status_code=404, detail="检索不存在")

        if existing_app.creator_id and current_user and existing_app.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权限修改此检索")

        update_data = {
            "name": app.name,
            "description": app.description,
            "avatar": app.avatar,
            "kb_ids": app.kb_ids,
            "similarity_threshold": app.similarity_threshold,
            "vector_similarity_weight": app.vector_similarity_weight,
            "rerank_id": app.rerank_id,
            "use_rerank": app.use_rerank,
            "top_k": app.top_k,
            "summary": app.summary,
            "llm_id": app.llm_id or DEFAULT_LLM_ID,
            "temperature": app.temperature,
            "top_p": app.top_p,
            "presence_penalty": app.presence_penalty,
            "frequency_penalty": app.frequency_penalty,
            "related_search": app.related_search,
            "query_mindmap": app.query_mindmap,
            "search_method": app.search_method or "dense",
        }

        success = await crud.update_search_app(db, app_id, **update_data)
        if not success:
            raise HTTPException(status_code=500, detail="更新失败")

        await db.commit()
        logger.info(f"更新搜索应用: {app_id} | 用户: {current_user.username if current_user else '匿名'}")
        return success_response(data={"id": app_id, "name": app.name})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新搜索应用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/search-apps/{app_id}")
async def delete_search_app(
    app_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """删除搜索应用"""
    try:
        app = await crud.get_search_app_by_id(db, app_id)
        if not app:
            raise HTTPException(status_code=404, detail="检索不存在")

        if app.creator_id and current_user and app.creator_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权限删除此检索")

        success = await crud.delete_search_app(db, app_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除失败")

        await db.commit()
        logger.info(f"删除搜索应用: {app_id} | 用户: {current_user.username if current_user else '匿名'}")
        return success_response(data={"id": app_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除搜索应用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 聊天应用管理 ====================

@router.post("/chat-apps")
async def create_chat_app(
    app: ChatAppCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """创建聊天应用"""
    try:
        user_id = current_user.id if current_user else None
        session_key = f"app_{int(time.time() * 1000)}"
        model_config = {
            "name": app.name,
            "icon": app.icon,
            "description": app.description,
            "prologue": app.prologue,
            "empty_response": app.empty_response,
            "kb_ids": app.kb_ids,
            "quote": app.quote,
            "keyword": app.keyword,
            "tts": app.tts,
            "similarity_threshold": app.similarity_threshold,
            "vector_similarity_weight": app.vector_similarity_weight,
            "top_n": app.top_n,
            "llm_id": app.llm_id,
            "temperature": app.temperature,
            "top_p": app.top_p,
        }
        if app.search_options:
            model_config["search_options"] = app.search_options
        if app.generate_options:
            model_config["generate_options"] = app.generate_options
        session = await crud.create_session(
            db=db,
            session_key=session_key,
            title=app.name,
            description=app.description,
            user_id=user_id,
            model_config=model_config,
        )
        await db.commit()
        logger.info(f"创建聊天应用: {app.name} | 用户: {current_user.username if current_user else '匿名'}")
        return success_response(data={"id": session.id, "session_key": session_key, "name": app.name})
    except Exception as e:
        logger.error(f"创建聊天应用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-apps")
async def get_chat_apps(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取聊天应用列表"""
    try:
        if not current_user:
            return success_response(data={"apps": []})
        
        sessions = await crud.get_user_sessions(db, current_user.id, limit=100)
        # 仅返回助手（app_ 开头且无 parent），并附带对话数量
        apps = []
        for s in sessions:
            if not s.session_key.startswith("app_") or s.parent_session_key:
                continue
            conv_count = await crud.count_conversations_by_app(db, s.session_key, current_user.id)
            apps.append({
                "id": s.id,
                "session_key": s.session_key,
                "name": s.model_config.get("name") if s.model_config else s.title,
                "icon": s.model_config.get("icon") if s.model_config else "",
                "description": (s.description or (s.model_config.get("description") if s.model_config else "")) or "",
                "prologue": s.model_config.get("prologue") if s.model_config else "",
                "empty_response": s.model_config.get("empty_response") if s.model_config else "",
                "kb_ids": s.model_config.get("kb_ids", []) if s.model_config else [],
                "quote": s.model_config.get("quote", True) if s.model_config else True,
                "keyword": s.model_config.get("keyword", False) if s.model_config else False,
                "tts": s.model_config.get("tts", False) if s.model_config else False,
                "search_options": s.model_config.get("search_options") if s.model_config else None,
                "generate_options": s.model_config.get("generate_options") if s.model_config else None,
                "conversation_count": conv_count,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            })
        return success_response(data={"apps": apps})
    except Exception as e:
        logger.error(f"获取聊天应用列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-apps/{session_key}")
async def get_chat_app(
    session_key: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取单个聊天应用详情（含 search_options、generate_options）"""
    try:
        session = await crud.get_session(db, session_key)
        if not session or not session.session_key.startswith("app_") or session.parent_session_key:
            raise HTTPException(status_code=404, detail="助手不存在")
        mc = session.model_config or {}
        app = {
            "id": session.id,
            "session_key": session.session_key,
            "name": mc.get("name") or session.title,
            "icon": mc.get("icon", ""),
            "description": (session.description or mc.get("description", "")) or "",
            "kb_ids": mc.get("kb_ids", []),
            "search_options": mc.get("search_options"),
            "generate_options": mc.get("generate_options"),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }
        return success_response(data=app)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取聊天应用详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat-apps/{app_session_key}/conversations")
async def get_app_conversations(
    app_session_key: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取某助手下所有对话列表"""
    try:
        app_session = await crud.get_session(db, app_session_key)
        if not app_session or not app_session.session_key.startswith("app_") or app_session.parent_session_key:
            raise HTTPException(status_code=404, detail="助手不存在")
        user_id = current_user.id if current_user else None
        convs = await crud.get_conversations_by_app(db, app_session_key, user_id=user_id)
        items = [
            {
                "session_key": s.session_key,
                "title": s.title,
                "updated_at": s.updated_at.isoformat(),
            }
            for s in convs
        ]
        return success_response(data={"conversations": items})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat-apps/{app_session_key}/conversations")
async def create_app_conversation(
    app_session_key: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """在助手下新建对话（配置继承自助手）"""
    try:
        app_session = await crud.get_session(db, app_session_key)
        if not app_session or not app_session.session_key.startswith("app_") or app_session.parent_session_key:
            raise HTTPException(status_code=404, detail="助手不存在")
        user_id = current_user.id if current_user else None
        conv_key = f"conv_{int(time.time() * 1000)}"
        await crud.create_session(
            db=db,
            session_key=conv_key,
            title="新对话",
            user_id=user_id,
            parent_session_key=app_session_key,
        )
        await db.commit()
        logger.info(f"创建对话: {conv_key} | 助手: {app_session_key}")
        return success_response(data={"session_key": conv_key, "title": "新对话"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/chat-apps/{session_key}")
async def update_chat_app(
    session_key: str,
    app: ChatAppCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新聊天应用"""
    try:
        session = await crud.get_session(db, session_key)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        mc = dict(session.model_config or {})
        mc.update({
            "name": app.name,
            "icon": app.icon,
            "description": app.description,
            "prologue": app.prologue,
            "empty_response": app.empty_response,
            "kb_ids": app.kb_ids,
            "quote": app.quote,
            "keyword": app.keyword,
            "tts": app.tts,
            "similarity_threshold": app.similarity_threshold,
            "vector_similarity_weight": app.vector_similarity_weight,
            "top_n": app.top_n,
            "llm_id": app.llm_id,
            "temperature": app.temperature,
            "top_p": app.top_p,
        })
        if app.search_options is not None:
            mc["search_options"] = app.search_options
        if app.generate_options is not None:
            mc["generate_options"] = app.generate_options
        await crud.update_session(
            db=db,
            session_key=session_key,
            title=app.name,
            description=app.description,
            model_config=mc,
        )
        await db.commit()
        logger.info(f"更新聊天应用: {session_key} | 用户: {current_user.username if current_user else '匿名'}")
        return success_response(data={"session_key": session_key, "name": app.name})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新聊天应用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/chat-apps/{session_key}/config")
async def update_chat_app_config(
    session_key: str,
    body: ChatAppConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """更新聊天应用对话配置（description、search_options、generate_options）"""
    try:
        session = await crud.get_session(db, session_key)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        mc = dict(session.model_config or {})
        update_kw = {}
        if body.description is not None:
            mc["description"] = body.description
            update_kw["description"] = body.description
        if body.search_options is not None:
            mc["search_options"] = body.search_options
        if body.generate_options is not None:
            mc["generate_options"] = body.generate_options
        update_kw["model_config"] = mc
        await crud.update_session(db=db, session_key=session_key, **update_kw)
        await db.commit()
        return success_response(data={"session_key": session_key})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新对话配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat-apps/{session_key}")
async def delete_chat_app(
    session_key: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """删除助手或对话（app_ 或 conv_）；删除助手时级联删除其下所有对话"""
    try:
        session = await crud.get_session(db, session_key)
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        if session_key.startswith("app_") and not session.parent_session_key:
            await crud.delete_conversations_by_app(db, session_key)
        await crud.delete_session(db, session_key)
        await db.commit()
        logger.info(f"删除会话: {session_key} | 用户: {current_user.username if current_user else '匿名'}")
        return success_response(data={"session_key": session_key})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/content")
async def get_document_content(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取文档完整内容（由 chunks 拼接）"""
    try:
        doc = await crud.get_document_by_id(db, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        kb = await crud.get_knowledge_base(db, doc.knowledge_base_id)
        if not kb or (not kb.is_public and kb.creator_id != (current_user.id if current_user else None)):
            raise HTTPException(status_code=403, detail="无权限访问此文档")

        chunks = await crud.get_chunks_by_document(db, document_id)
        full_content = "\n\n".join([chunk.content for chunk in chunks]) if chunks else ""

        return success_response(data={
            "document_id": doc.id,
            "filename": doc.filename,
            "file_path": doc.file_path,
            "file_size": doc.file_size,
            "file_type": doc.file_type,
            "content": full_content,
            "chunk_count": doc.chunk_count,
            "created_at": doc.created_at.isoformat(),
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档内容失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_query_history(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """获取查询历史记录，直接根据当前用户获取所有历史记录"""
    try:
        query_logs = await crud.get_query_logs_by_user(
            db=db,
            user_id=str(current_user.id) if current_user else None
        )

        history_records = []
        for log in query_logs:
            # 解析sources JSON
            sources = []
            if log.sources:
                try:
                    sources = json.loads(log.sources) if isinstance(log.sources, str) else log.sources
                except:
                    sources = []

            # 解析model_config JSON
            model_config = {}
            if log.model_config:
                try:
                    model_config = json.loads(log.model_config) if isinstance(log.model_config, str) else log.model_config
                except:
                    model_config = {}

            history_records.append({
                "id": log.id,
                "query": log.query,
                "answer": log.answer,
                "sources": sources,
                "sources_count": len(sources),
                "status": "success" if log.success else "error",
                "created_at": log.created_at.isoformat(),
                "knowledge_base_id": log.knowledge_base_id,
                "search_app_id": log.search_app_id,
                "model_config": model_config,
                # 单独提取参数配置字段，方便前端使用
                "llm_id": model_config.get("llm_id"),
                "temperature": model_config.get("temperature"),
                "top_p": model_config.get("top_p"),
                "search_method": model_config.get("search_method"),
                "similarity_threshold": model_config.get("similarity_threshold")
            })

        return success_response(data={
            "records": history_records,
            "total": len(history_records)  # 这里可以优化为实际总数
        })

    except Exception as e:
        logger.error(f"获取查询历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{log_id}")
async def delete_query_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """删除单条查询日志"""
    try:
        log = await crud.get_query_log_by_id(db, log_id)
        if not log:
            raise HTTPException(status_code=404, detail="查询日志不存在")

        # 检查权限：只能删除自己的查询日志
        if current_user and log.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="无权限删除此记录")

        success = await crud.delete_query_log(db, log_id)
        if not success:
            raise HTTPException(status_code=500, detail="删除失败")

        await db.commit()
        return success_response(msg="查询日志已删除")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除查询日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history")
async def clear_query_logs(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """清空当前用户的所有查询日志"""
    try:
        logger.info(f"清空查询日志，用户: {current_user.username if current_user else '匿名'}")
        deleted_count = await crud.clear_query_logs_by_user(
            db=db,
            user_id=str(current_user.id) if current_user else None
        )

        logger.info(f"清空完成，删除 {deleted_count} 条记录")

        await db.commit()
        return success_response(
            data={"deleted_count": deleted_count},
            msg=f"已清空 {deleted_count} 条查询日志"
        )

    except Exception as e:
        logger.error(f"清空查询日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

