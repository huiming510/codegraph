"""RAG System API - 应用入口，挂载各模块路由"""
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

from config import settings, get_llm_config
from llm import get_llm, LLMConfig
from database import get_db, init_db, close_db, crud
from logger import setup_logger, logger, LoggingMiddleware

from routers.common import success_response
from routers import auth, users, permissions, knowledge_bases, documents, llm as llm_router, embedding, config, rag, logs


# 生命周期管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logger()
    logger.info("正在初始化数据库...")
    try:
        await init_db()
        logger.info("数据库初始化完成")
        await init_sample_data()
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        logger.warning("将使用内存模式运行")
    # 启动解析服务 worker（走 server 逻辑，解析/上传不请求外部 HTTP）
    # 同进程时注入「就地回调」：ES 上传成功后直接更新文档状态，避免 HTTP 回调连接失败
    import os
    _file_worker_task = None
    try:
        from server import component as server_component
        from database.connection import AsyncSessionLocal

        async def _update_doc_status_callback(doc_id: str, status: str, chunk_count: int = 0, message: str = ""):
            try:
                async with AsyncSessionLocal() as db:
                    await crud.update_document_status(
                        db, int(doc_id), status,
                        chunk_count=chunk_count if status == "completed" else None,
                    )
                    await db.commit()
                logger.info(f"文档解析状态已更新: doc_id={doc_id}, status={status}, chunk_count={chunk_count}")
            except Exception as e:
                logger.exception(f"就地更新文档状态失败: doc_id={doc_id}, error={e}")

        server_component.parse_status_callback = _update_doc_status_callback
        from server.file import file_worker
        from server.component import task_queue, es_client
        _file_worker_task = asyncio.create_task(file_worker())
        logger.info("解析服务 worker 已启动（文档解析与上传走 server 逻辑）")
    except Exception as e:
        logger.warning(f"解析服务 worker 未启动（文档将仅入库不解析）: {e}")
    yield
    if _file_worker_task is not None:
        try:
            from server.component import task_queue, es_client
            await task_queue.join()
            await es_client.es.close()
        except Exception as e:
            logger.warning(f"关闭解析服务资源: {e}")
    logger.info("正在关闭数据库连接...")
    try:
        await close_db()
    except Exception:
        pass
    logger.info("应用已关闭")


async def init_sample_data():
    """初始化示例数据"""
    from database.connection import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await crud.init_default_permissions(db)
        logger.info("默认权限初始化完成")

        admin = await crud.get_user_by_username(db, "admin")
        if not admin:
            await crud.create_user(
                db=db,
                username="admin",
                password="admin123",
                nickname="管理员",
                role="admin",
            )
            await db.commit()
            logger.info("已创建默认管理员账户: admin/admin123")

        logger.info("初始化完成")


app = FastAPI(title="RAG System API", lifespan=lifespan)

app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        msg = detail.get("msg", str(detail))
    elif isinstance(detail, list):
        msg = "; ".join(
            f"{e.get('loc', [])}: {e.get('msg', '')}" for e in detail if isinstance(e, dict)
        ) or str(detail)
    else:
        msg = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "data": None, "msg": msg},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"未捕获异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"code": 500, "data": None, "msg": str(exc) or "服务器内部错误"},
    )


# 初始化 LLM 并注入到路由模块
llm_config = get_llm_config()
llm = get_llm(llm_config)
llm_router.set_llm(llm)
rag.set_llm(llm)
embedding.set_embedding_config({
    "provider": "openai",
    "model": "text-embedding-3-small",
    "api_key": None,
    "api_base": None,
    "dimensions": 1536,
})


@app.get("/")
def read_root():
    frontend_index = _get_frontend_index_file()
    if frontend_index is not None:
        return FileResponse(frontend_index)
    return success_response(
        data={"message": "RAG System API", "llm_provider": llm.get_provider_name()}
    )


def _get_frontend_dist_dir() -> Path | None:
    if not settings.serve_frontend:
        return None
    backend_dir = Path(__file__).resolve().parent
    frontend_dist = Path(settings.frontend_dist_dir)
    if not frontend_dist.is_absolute():
        frontend_dist = (backend_dir / frontend_dist).resolve()
    if not frontend_dist.exists():
        logger.warning(f"启用了 SERVE_FRONTEND，但目录不存在: {frontend_dist}")
        return None
    return frontend_dist


def _get_frontend_index_file() -> str | None:
    frontend_dist = _get_frontend_dist_dir()
    if frontend_dist is None:
        return None
    index_file = frontend_dist / "index.html"
    if not index_file.exists():
        logger.warning(f"前端入口文件不存在: {index_file}")
        return None
    return str(index_file)


def _get_frontend_assets_dir() -> Path | None:
    frontend_dist = _get_frontend_dist_dir()
    if frontend_dist is None:
        return None
    assets_dir = frontend_dist / "assets"
    if not assets_dir.exists():
        logger.warning(f"前端 assets 目录不存在: {assets_dir}")
        return None
    return assets_dir.resolve()


def _resolve_asset_file(asset_path: str) -> Path | None:
    assets_dir = _get_frontend_assets_dir()
    if assets_dir is None:
        return None
    target = (assets_dir / asset_path).resolve()
    try:
        target.relative_to(assets_dir)
    except ValueError:
        return None
    try:
        if not target.exists() or not target.is_file():
            return None
    except OSError:
        return None
    return target


def _resolve_frontend_file(relative_path: str) -> Path | None:
    frontend_dist = _get_frontend_dist_dir()
    if frontend_dist is None:
        return None
    target = (frontend_dist / relative_path).resolve()
    try:
        target.relative_to(frontend_dist)
    except ValueError:
        return None
    try:
        if not target.exists() or not target.is_file():
            return None
    except OSError:
        return None
    return target


# 挂载路由（权限 / 登录 / 用户 分开）
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(permissions.router)
app.include_router(knowledge_bases.router)
app.include_router(documents.router)
app.include_router(llm_router.router)
app.include_router(embedding.router)
app.include_router(config.router)
app.include_router(rag.router)
app.include_router(logs.router)


@app.api_route("/assets/{asset_path:path}", methods=["GET", "HEAD"])
async def frontend_assets(asset_path: str):
    file_path = _resolve_asset_file(asset_path)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(str(file_path))


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")
    if full_path in {"docs", "redoc", "openapi.json"}:
        raise HTTPException(status_code=404, detail="Not Found")

    static_file = _resolve_frontend_file(full_path)
    if static_file is not None:
        return FileResponse(str(static_file))

    frontend_index = _get_frontend_index_file()
    if frontend_index is None:
        raise HTTPException(status_code=404, detail="Not Found")
    return FileResponse(frontend_index)
