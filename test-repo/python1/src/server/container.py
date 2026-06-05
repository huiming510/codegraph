# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/5 09:22
# @Author  : cuils
# @Description:
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any
from starlette import status
from pydantic import BaseModel
from fastapi import APIRouter
from cachetools import LRUCache
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)

from src.index import (
    VllmEmbedding,
    VllmReranker,
    AsyncRetriever,
    AsyncElasticsearchClient
)
from src.llm import AsyncOpenAIModel
from src.memory import ContextManager
from src.storage import Base, ContextPersistent, DocumentPersistent
from src.preprocess.text_pipeline import TextPipeline
from src.utils import load_config, get_logger

# 缓存目录: 日志、文件、数据库
CACHE_DIR = Path(os.environ["HOME"]) / ".linkrag"
LOG_DIR = CACHE_DIR / "logs"
FILE_DIR = CACHE_DIR / "files"
DB_DIR = CACHE_DIR / "db"
LOG_DIR.mkdir(parents=True, exist_ok=True)
FILE_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)

# 获取初始默认配置参数
DEFAULT_CONFIG = load_config(Path(__file__).parent.parent / "config.yml")

# 初始化logger
app_logger = get_logger(name="app_logger", log_file=LOG_DIR / "app.log")  # 记录app运行情况
file_logger = get_logger(name="file_logger", log_file=LOG_DIR / "file.log")  # 记录文件处理情况
rag_logger = get_logger(
    name="rag_logger",
    log_file=LOG_DIR / "rag.log",
    add_es=True,
    es_hosts=DEFAULT_CONFIG["elasticsearch"]["url"]
)  # 记录rag情况，请求和结果均写入es


class ModelConfig(BaseModel):
    model: str
    base_url: str
    api_key: str = "EMPTY"
    thinking: bool = False


class ChunkConfig(BaseModel):
    index: str # 知识库索引名称
    chunk_size: int = 512
    chunk_overlap: int = 0
    chunk_strategy: str = "general"


class APIResponse(BaseModel):
    status: int = status.HTTP_200_OK
    msg: str | None = None


class AppContainer:
    # 模型
    llm_models: Dict[str, AsyncOpenAIModel] = dict()  # llm模型
    embedding_model: VllmEmbedding = None  # embedding模型
    reranker_model: VllmReranker = None  # reranker模型

    # 检索与存储
    es_client: AsyncElasticsearchClient = None  # es
    db_engine: AsyncEngine = None
    db_session_factory: async_sessionmaker[AsyncSession] = None
    retriever: AsyncRetriever = None  # 检索

    # 知识库文档处理与存储
    file_queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=65536)  # 文件处理队列
    file_persistent: DocumentPersistent = None
    kb_text_pipeline_mapping: Dict[str, TextPipeline] = dict()
    kb_code_pipeline_mapping: Dict[str, Any] = dict()

    # 上下文管理
    context_manager: ContextManager = None

    # api接口路由
    router = APIRouter(prefix="/api", tags=["api"])

    def __init__(self):
        self.config: Dict[str, Any] = DEFAULT_CONFIG

        self.router.add_api_route("/update_model", endpoint=self.update_models, methods=["POST"])
        self.router.add_api_route("/update_text_pipeline", endpoint=self.update_text_pipeline, methods=["POST"])

    async def init(self):
        app_logger.info("Initializing...")
        await self.init_db()
        app_logger.info("-DB Engine and Tables initialized.")
        info = await self.init_es_client()
        app_logger.info(f"-Elasticsearch Connection initialized. {info}")
        self.init_models()
        app_logger.info("-LLM Models initialized.")
        self.init_embedding_model()
        app_logger.info("-Embedding Model initialized.")
        self.init_reranker()
        app_logger.info("-Reranker Model initialized.")
        # embedding 和 es初始化要在retriever之前
        self.init_retriever()
        app_logger.info("-Retriever initialized.")
        self.init_text_pipeline()
        app_logger.info("-Text Pipeline initialized.")
        self.init_context_manager()
        app_logger.info("-Context Manager initialized.")
        self.init_file_persistent()
        app_logger.info("-File Persistent initialized.")

    async def close(self):
        # 关闭模型连接
        app_logger.info("Closing...")
        for name in self.llm_models:
            await self.llm_models[name].close()
        app_logger.info("-LLM Models closed.")
        # 关闭es连接
        await self.es_client.close()
        app_logger.info("-Elasticsearch Connection closed.")
        # 关闭db连接
        await self.db_engine.dispose()
        app_logger.info("-DB Connection closed.")

    def init_models(self):
        for conf in self.config["llm"]:
            llm = AsyncOpenAIModel(
                model=conf["model"],
                base_url=conf["base_url"],
                api_key=conf["api_key"],
                thinking=conf["thinking"],
                max_model_len=conf["max_model_len"]
            )
            self.llm_models[conf["model"]] = llm

    async def init_es_client(self):
        self.es_client = AsyncElasticsearchClient(
            url=self.config["elasticsearch"]["url"]
        )
        info = await self.es_client.es.info()
        return info

    def init_db_engine_and_session(self):
        self.db_engine = create_async_engine(
            url=f"sqlite+aiosqlite:///{DB_DIR}/linkrag.db",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False
        )
        self.db_session_factory = async_sessionmaker(
            bind=self.db_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )

    async def init_db_tables(self):
        if not self.db_engine:
            raise Exception("Sqlite engine not initialized.")
        async with self.db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def init_db(self):
        self.init_db_engine_and_session()
        await self.init_db_tables()

    def init_retriever(self):
        if self.embedding_model and self.es_client:
            self.retriever = AsyncRetriever(
                embedding_client=self.embedding_model,
                es_client=self.es_client
            )
        else:
            app_logger.error("-Embedding model and ES not initialized.")
            raise RuntimeError("Embedding model and ES not initialized.")

    def init_embedding_model(self):
        self.embedding_model = VllmEmbedding(
            url=self.config["embedding"]["base_url"],
            model=self.config["embedding"]["model"],
            support_matryoshka=self.config["embedding"]["support_matryoshka"],
            dimensions=self.config["embedding"]["dimensions"]
        )

    def init_reranker(self):
        if self.config["reranker"]:
            self.reranker_model = VllmReranker(
                url=self.config["reranker"]["base_url"],
                model=self.config["reranker"]["model"],
                llm_arch=self.config["reranker"]["llm_arch"],
            )

    def init_text_pipeline(self):
        default_text_pipeline = TextPipeline(
            chunk_size=4096,
            chunk_overlap=256,
            chunk_strategy="general",
            logger=file_logger,
            cache_dir=FILE_DIR
        )
        self.kb_text_pipeline_mapping["default"] = default_text_pipeline

    def init_context_manager(self):
        if self.db_session_factory:
            self.context_manager = ContextManager(
                cache_size=128,
                persistent=ContextPersistent(session_factory=self.db_session_factory)
            )
        else:
            raise Exception("DB not initialized.")

    def init_file_persistent(self):
        if self.db_session_factory:
            self.file_persistent = DocumentPersistent(session_factory=self.db_session_factory)
        else:
            raise Exception("DB not initialized.")

    async def update_models(self, model_config: ModelConfig):
        """更新模型"""
        try:
            self.llm_models[model_config.model] = AsyncOpenAIModel(
                model=model_config.model,
                base_url=model_config.base_url,
                api_key=model_config.api_key,
                thinking=model_config.thinking
            )
            return APIResponse(status=status.HTTP_200_OK, msg="Success")
        except Exception as e:
            return APIResponse(status=status.HTTP_406_NOT_ACCEPTABLE, msg=str(e))

    async def update_text_pipeline(self, chunk_config: ChunkConfig):
        try:
            kb_text_pipeline = TextPipeline(
                chunk_size=chunk_config.chunk_size,
                chunk_overlap=chunk_config.chunk_overlap,
                chunk_strategy=chunk_config.chunk_strategy,
                logger=file_logger,
                cache_dir=FILE_DIR
            )
            self.kb_text_pipeline_mapping[chunk_config.index] = kb_text_pipeline
            return APIResponse(status=status.HTTP_200_OK, msg="Success")
        except Exception as e:
            return APIResponse(status=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=str(e))


app_container = AppContainer()
