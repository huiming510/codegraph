# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/28 17:12
# @Author  : cuils
# @Description:
file文件管理接口
"""
import json
import uuid
import asyncio
import aiofiles
import traceback
from pathlib import Path
from starlette import status
from pydantic import BaseModel
from fastapi import APIRouter, File, UploadFile, Form

from src.storage import FileStatus
from src.server.container import app_container, file_logger, FILE_DIR

router = APIRouter(prefix="/file", tags=["file"])


async def file_worker():
    """文件处理 worker"""
    loop = asyncio.get_event_loop()
    while True:
        task: FileRequest = await app_container.file_queue.get()
        doc_id, filepath, index = task.doc_id, task.filepath, task.index
        # 更新文档状态
        await app_container.file_persistent.update_document(
            doc_id=doc_id,
            status=FileStatus.PROCESSING
        )
        try:
            # 解析分块
            if index in app_container.kb_text_pipeline_mapping:
                fn = app_container.kb_text_pipeline_mapping[index].run
            else:
                fn = app_container.kb_text_pipeline_mapping["default"].run
            chunks = await asyncio.wait_for(
                loop.run_in_executor(None, fn, filepath, doc_id),
                timeout=3600
            )

            if not chunks:
                await app_container.file_persistent.update_document(doc_id=doc_id, status=FileStatus.FAILED)
                continue
            else:
                await app_container.file_persistent.update_document(
                    doc_id=doc_id,
                    status=FileStatus.PROCESSING,
                    num_chunks=len(chunks)
                )

            # embedding计算
            texts = [chunk.content for chunk in chunks]
            embeddings = await app_container.embedding_model.abatch_encode(texts)

            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = [round(num, 8) for num in embedding]
                chunk.embedding_model = app_container.embedding_model.model

            # 写入ES索引
            for chunk in chunks:
                await app_container.es_client.es.index(
                    index=index,
                    id=chunk.chunk_id,
                    body=chunk.model_dump()
                )

            file_logger.info(f"{doc_id}-{filepath}-{index}, DONE")

            await app_container.file_persistent.update_document(
                doc_id=doc_id,
                status=FileStatus.COMPLETED
            )
        except Exception:
            file_logger.error(f"[Error]: {traceback.print_exc()}")
            await app_container.file_persistent.update_document(
                doc_id=doc_id,
                status=FileStatus.FAILED
            )
        finally:
            app_container.file_queue.task_done()


class FileRequest(BaseModel):
    doc_id: str = None
    filepath: str|Path = None
    index: str


class FileResponse(BaseModel):
    doc_id: str
    status: int = status.HTTP_202_ACCEPTED
    index: str
    msg: str = None


@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_file(request: FileRequest):
    """上传单个文件"""
    if request.doc_id is None:
        request.doc_id = str(uuid.uuid4())
    await app_container.file_queue.put(request)
    return FileResponse(doc_id=request.doc_id, status=status.HTTP_202_ACCEPTED, index=request.index)


@router.post("/upload_stream", status_code=status.HTTP_202_ACCEPTED)
async def upload_file_stream(
    doc_id: str = Form(...),
    index: str = Form(...),
    file: UploadFile = File(...)
):
    """流式上传单个文件"""
    filename = file.filename
    cache_filepath = FILE_DIR / index / filename
    cache_filepath.parent.mkdir(parents=True, exist_ok=True)

    # 写入db
    await app_container.file_persistent.insert_document(
        doc_id=doc_id,
        index=index,
        filename=filename,
        file_path=str(cache_filepath),
        file_size=file.size,
        file_type=cache_filepath.suffix
    )

    async with aiofiles.open(cache_filepath, "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            await f.write(chunk)

    request = FileRequest(
        doc_id=doc_id,
        filepath=cache_filepath,
        index=index,
    )
    if request.doc_id is None:
        request.doc_id = str(uuid.uuid4())

    # 文件上传成功，更新状态
    await app_container.file_persistent.update_document(doc_id=request.doc_id, status=FileStatus.UPLOADED)
    # 入队
    await app_container.file_queue.put(request)
    return FileResponse(doc_id=request.doc_id, status=status.HTTP_202_ACCEPTED, index=request.index)


@router.get("/list")
async def get_file_list():
    """暂不支持文件一览"""
    return


@router.delete("/delete")
async def delete_file():
    """暂不支持文件删除"""
    return