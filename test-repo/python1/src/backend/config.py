"""应用配置"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings

# .env 固定从 config 所在目录加载，避免因启动目录不同而加载不到
_DOTENV = Path(__file__).resolve().parent / ".env"
from llm.base import LLMProvider, LLMConfig


class Settings(BaseSettings):
    """应用设置"""
    # LLM配置
    llm_provider: str = "mock"
    llm_model: str = "gpt-3.5-turbo"
    llm_api_key: Optional[str] = None
    llm_api_base: Optional[str] = None
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    
    # Azure专用
    azure_deployment: Optional[str] = None
    azure_api_version: str = "2024-02-01"
    
    # 应用配置
    upload_dir: str = "uploads"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://localhost:5174"
    # 是否由后端直接托管前端静态资源（无 Nginx 一体化部署）
    serve_frontend: bool = False
    # 前端 dist 目录（serve_frontend=true 时生效）
    frontend_dist_dir: str = "../frontend/dist"
    # 解析服务地址（用于按服务器路径解析入库，为空则仅创建文档记录）
    linkrag_server_url: Optional[str] = None
    # QA 流程服务地址（单轮 RAG 问答检索，不填则用 linkrag_server_url）
    qa_service_url: Optional[str] = None
    # 多轮流式对话外部 API 地址，如 http://192.168.10.187:8000
    chat_stream_url: Optional[str] = "http://192.168.10.187:8000"
    # 解析完成后回调的本机地址（供 server 回调更新文档状态），如 http://127.0.0.1:8000；不填时 backend 启动会设为该默认值
    backend_base_url: Optional[str] = None
    # 解析服务写入的 ES 索引名，需与 linkrag config.yml 中 elasticsearch.index 一致
    linkrag_es_index: str = "linkrag"
    # Elasticsearch 连接（与 config.yml elasticsearch 对应，可选环境变量回退）
    elasticsearch_url: Optional[str] = None
    elasticsearch_username: Optional[str] = None
    elasticsearch_password: Optional[str] = None
    # Embedding 服务（解析时向量化，可选；未配置时解析服务使用 config.yml）
    embedding_base_url: Optional[str] = None
    embedding_model: Optional[str] = None
    
    # 数据库配置
    # 优先使用 DATABASE_URL（例如 postgresql+asyncpg://user:pass@host:5432/dbname）
    database_url: Optional[str] = None
    # 可选：同步 URL（当前仅在需要同步引擎时使用）
    database_sync_url: Optional[str] = None
    # SQLite 兼容配置（当 DATABASE_URL 未设置时生效）
    sqlite_database: str = "linkrag.db"
    
    # 日志配置
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_to_db: bool = False
    log_retention_days: int = 30
    
    # 上下文配置
    context_max_history: int = 10
    context_max_tokens: int = 4000
    
    class Config:
        env_file = str(_DOTENV) if _DOTENV.exists() else ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外字段


def get_llm_config() -> LLMConfig:
    """从环境变量获取LLM配置"""
    settings = Settings()
    
    # 转换provider字符串为枚举
    try:
        provider = LLMProvider(settings.llm_provider.lower())
    except ValueError:
        provider = LLMProvider.MOCK
    
    return LLMConfig(
        provider=provider,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        api_base=settings.llm_api_base,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        azure_deployment=settings.azure_deployment,
        azure_api_version=settings.azure_api_version,
    )


settings = Settings()
