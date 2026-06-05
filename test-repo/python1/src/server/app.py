# -*- coding: utf-8 -*-
"""
# @Time    : 2026/1/28 16:47
# @Author  : cuils
# @Description:
"""
import asyncio
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from .container import app_container, app_logger
from .kb import router as kb_router
from .file import router as file_router, file_worker
from .qa import router as qa_router
from .chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动阶段
    app.state.container = app_container
    await app.state.container.init()
    task = asyncio.create_task(file_worker())
    app.state.worker_task = task

    # 运行阶段
    yield

    # 关闭阶段
    await app.state.container.file_queue.join()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        app_logger.info("File worker cancelled.")
    await app.state.container.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kb_router)
app.include_router(file_router)
app.include_router(qa_router)
app.include_router(chat_router)
app.include_router(app_container.router)


@app.get("/health")
async def health_check():
    return {"status": 200}


if __name__ == '__main__':
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True, workers=1)
