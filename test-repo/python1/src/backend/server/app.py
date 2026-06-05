# -*- coding: utf-8 -*-
"""
解析服务 FastAPI 应用：文档上传解析(file) + 索引管理(index)。
可单独启动：uvicorn server.app:app --host 0.0.0.0 --port 8000
需在 src 目录或设置 PYTHONPATH 包含 backend 的父级，以便 server 可导入。
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .db import router as db_router
from .file import router as file_router, file_worker
from .component import task_queue, es_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(file_worker())
    yield
    await task_queue.join()
    await es_client.es.close()


app = FastAPI(title="LinkRAG 解析服务", lifespan=lifespan)
app.include_router(db_router)
app.include_router(file_router)
