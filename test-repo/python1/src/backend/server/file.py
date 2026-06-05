# -*- coding: utf-8 -*-
"""
文档上传与解析接口：与 src/server/file.py 调用一致，仅写入的 ES 索引(es_id)由请求指定。
按路径解析(/file/upload)、按上传文件解析(/file/upload-file)。
"""
import re
import uuid
import traceback
import asyncio
from pathlib import Path
from starlette import status
from typing import Optional
from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

from . import component as _component
from .component import (
    task_queue,
    pipeline,
    es_client,
    embed_client,
    upload_dir,
    backend_callback_url,
    file_logger,
)
import httpx
from index import VllmEmbedding

router = APIRouter(prefix="/file", tags=["file"])


def _safe_dirname(name: str) -> str:
    """将知识库名等转为可作目录名的字符串（与 src/server/file.py 一致）"""
    if not name or not name.strip():
        return "default"
    s = re.sub(r'[<>:"/\\|?*]', "_", name.strip())
    return s[:100] or "default"


async def _notify_parse_status(doc_id: str, status: str, chunk_count: int = 0, message: str = ""):
    """解析完成后更新文档状态：优先同进程回调直接写库，否则请求 backend parse-status 接口"""
    if not doc_id:
        return
    cb = getattr(_component, "parse_status_callback", None)
    if cb:
        try:
            await cb(doc_id, status, chunk_count, message)
            return
        except Exception as e:
            file_logger.warning(f"[file] 就地回调解析状态失败: doc_id={doc_id}, error={e}")
    if not backend_callback_url:
        return
    url = f"{backend_callback_url.rstrip('/')}/api/documents/{doc_id}/parse-status"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                url,
                json={"status": status, "chunk_count": chunk_count, "message": message},
            )
    except Exception as e:
        file_logger.warning(f"[file] 回调解析状态失败: doc_id={doc_id}, error={e}")


async def file_worker():
    """文件处理 worker：与 src/server/file.py 一致，解析 → 分块 → 向量化 → 写入 ES（index=es_id 由请求传入）"""
    while True:
        task: "FileRequest" = await task_queue.get()
        doc_id = task.id
        try:
            doc_id, filepath, index = task.id, task.filepath, task.index
            file_logger.info(f"[解析] 开始处理 doc_id={doc_id} filepath={filepath} index={index}")
            chunks = await asyncio.to_thread(pipeline.run, filepath, doc_id)
            file_logger.info(f"[解析] 分块完成 doc_id={doc_id} chunks={len(chunks)}")
            if not chunks:
                file_logger.warning(f"[解析] 解析结果为空 doc_id={doc_id}，回调为失败")
                await _notify_parse_status(doc_id, "failed", message="解析结果为空")
                continue

            texts = [chunk.content for chunk in chunks]
            base_url = (getattr(task, "embedding_base_url", None) or "").strip()
            if base_url:
                _embed = VllmEmbedding(
                    url=base_url,
                    model=(getattr(task, "embedding_model", None) or "Qwen3-Embedding-0.6B").strip() or "Qwen3-Embedding-0.6B",
                    support_matryoshka=False,
                    dimensions=1024,
                )
                embeddings = await _embed.abatch_encode(texts)
                embedding_model_name = _embed.model
            else:
                embeddings = await embed_client.abatch_encode(texts)
                embedding_model_name = embed_client.model
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = [round(num, 8) for num in embedding]
                chunk.embedding_model = embedding_model_name

            for chunk in chunks:
                await es_client.es.index(
                    index=index,
                    id=chunk.chunk_id,
                    body=chunk.model_dump(),
                )
            file_logger.info(f"[解析] 完成 doc_id={doc_id} index={index} 已写入 {len(chunks)} 个切片")
            await _notify_parse_status(doc_id, "completed", chunk_count=len(chunks))
        except Exception as e:
            file_logger.exception(f"[解析] 失败 doc_id={doc_id} error={e}")
            print(e)
            traceback.print_exc()
            await _notify_parse_status(doc_id, "failed", message=str(e))
        finally:
            task_queue.task_done()


class FileRequest(BaseModel):
    """解析任务：与 src/server/file.py 及 client 约定一致，index 即写入的 es_id"""
    id: Optional[str] = None
    filepath: Optional[str] = ""
    index: Optional[str] = "poc"
    embedding_base_url: Optional[str] = None
    embedding_model: Optional[str] = None


class FileResponse(BaseModel):
    id: str
    status: int
    index: str
    msg: str = None


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_by_path(request: FileRequest):
    """按服务器路径提交解析任务（JSON body: id, filepath, index），index 即写入的 es_id"""
    if request.id is None:
        request.id = str(uuid.uuid4())
    if not request.filepath or not Path(request.filepath).exists():
        return FileResponse(id=request.id, status=400, index=request.index or "poc", msg="文件路径不存在")
    await task_queue.put(request)
    return FileResponse(id=request.id, status=status.HTTP_202_ACCEPTED, index=request.index or "poc")


@router.post("/upload-file", status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    file: UploadFile = File(...),
    id: str = Form(..., description="文档 ID，与 backend 的 doc.id 一致"),
    index: str = Form("poc", description="写入 ES 的索引名，须与知识库 es_id 或 linkrag_kb_{id} 一致"),
    knowledge_base_name: str = Form("default", description="知识库名称，用于组织保存路径"),
    embedding_base_url: Optional[str] = Form(None, description="Embedding 服务地址，与 ES 环境配置一致可防解析报错"),
    embedding_model: Optional[str] = Form(None, description="Embedding 模型名"),
):
    """
    接收前端经 backend 转发的文件流，保存到本地后入队解析并写入 ES。
    与 src/server/file.py 及 LinkragServerClient.upload_file_for_parse_async 约定一致；index 即 es_id。
    """
    if not file.filename:
        return FileResponse(id=id, status=400, index=index, msg="缺少文件名")

    kb_safe = _safe_dirname(knowledge_base_name)
    save_dir = Path(upload_dir) / kb_safe / id
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)
    file_path_str = str(file_path.resolve())

    req = FileRequest(id=id, filepath=file_path_str, index=index)
    if embedding_base_url and embedding_base_url.strip():
        req.embedding_base_url = embedding_base_url.strip()
    if embedding_model and embedding_model.strip():
        req.embedding_model = embedding_model.strip()
    await task_queue.put(req)
    return FileResponse(id=id, status=status.HTTP_202_ACCEPTED, index=index)


@router.get("/list")
async def get_file_list():
    """暂不支持文件一览"""
    return {"message": "not implemented"}


@router.delete("/delete")
async def delete_file():
    """暂不支持文件删除"""
    return {"message": "not implemented"}
