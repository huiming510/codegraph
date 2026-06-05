"""数据库连接管理 - SQLite"""
import json
import os
from typing import AsyncGenerator
from sqlalchemy import text, create_engine, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# 延迟导入避免循环依赖
def get_database_url():
    from config import settings
    if settings.database_url:
        return settings.database_url
    # SQLite 路径：统一为绝对路径并使用正斜杠（兼容 Windows）
    db_path = os.path.abspath(settings.sqlite_database).replace("\\", "/")
    return f"sqlite+aiosqlite:///{db_path}"


def _get_sync_database_url():
    """同步引擎用 URL（目前用于 SQLite 启动前同步迁移）"""
    from config import settings
    if settings.database_sync_url:
        return settings.database_sync_url
    db_path = os.path.abspath(settings.sqlite_database).replace("\\", "/")
    return f"sqlite:///{db_path}"


def _is_sqlite_backend() -> bool:
    return get_database_url().startswith("sqlite")


def _get_engine_kwargs(database_url: str) -> dict:
    kwargs = {"echo": False}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        kwargs["poolclass"] = StaticPool
    return kwargs

# 创建异步引擎（延迟初始化）
engine = None
AsyncSessionLocal = None

def init_engine():
    global engine, AsyncSessionLocal
    if engine is None:
        database_url = get_database_url()
        engine = create_async_engine(
            database_url,
            **_get_engine_kwargs(database_url),
        )
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return engine, AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（依赖注入用）"""
    _, session_local = init_engine()
    async with session_local() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _add_es_id_if_missing(sync_conn):
    """为 knowledge_bases 添加 es_id 列（兼容旧库，无则添加）"""
    cols = _get_table_columns(sync_conn, "knowledge_bases")
    if "es_id" not in cols:
        sync_conn.execute(text("ALTER TABLE knowledge_bases ADD COLUMN es_id VARCHAR(100) NULL"))


def _backfill_es_id_if_empty(sync_conn):
    """为历史知识库补齐 es_id（空值回填为 linkrag_kb_{id}）。"""
    sync_conn.execute(
        text(
            """
            UPDATE knowledge_bases
            SET es_id = 'linkrag_kb_' || id
            WHERE es_id IS NULL OR TRIM(es_id) = ''
            """
        )
    )


def _add_parent_session_key_if_missing(sync_conn):
    """为 chat_sessions 添加 parent_session_key 列（对话所属助手）"""
    cols = _get_table_columns(sync_conn, "chat_sessions")
    if "parent_session_key" not in cols:
        sync_conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN parent_session_key VARCHAR(100) NULL"))


def _add_description_if_missing(sync_conn):
    """为 chat_sessions 添加 description 列（助手角色描述）"""
    cols = _get_table_columns(sync_conn, "chat_sessions")
    if "description" not in cols:
        sync_conn.execute(text("ALTER TABLE chat_sessions ADD COLUMN description TEXT NULL"))


def _add_chunk_params_if_missing(sync_conn):
    """为 knowledge_bases 添加 chunk_size、chunk_overlap、chunk_strategy 列（兼容旧库）"""
    cols = _get_table_columns(sync_conn, "knowledge_bases")
    if "chunk_size" not in cols:
        sync_conn.execute(text("ALTER TABLE knowledge_bases ADD COLUMN chunk_size INTEGER DEFAULT 4096"))
    if "chunk_overlap" not in cols:
        sync_conn.execute(text("ALTER TABLE knowledge_bases ADD COLUMN chunk_overlap INTEGER DEFAULT 256"))
    if "chunk_strategy" not in cols:
        sync_conn.execute(text("ALTER TABLE knowledge_bases ADD COLUMN chunk_strategy VARCHAR(50) DEFAULT 'general'"))


def _add_query_logs_search_app_id_if_missing(sync_conn):
    """为 query_logs 添加 search_app_id 列（兼容旧库，关联检索应用）"""
    cols = _get_table_columns(sync_conn, "query_logs")
    if "search_app_id" not in cols:
        sync_conn.execute(text("ALTER TABLE query_logs ADD COLUMN search_app_id INTEGER NULL"))


def _add_embedding_model_if_missing(sync_conn):
    """为 knowledge_bases 添加 embedding_model 列（设计文档要求）"""
    cols = _get_table_columns(sync_conn, "knowledge_bases")
    if "embedding_model" not in cols:
        sync_conn.execute(text("ALTER TABLE knowledge_bases ADD COLUMN embedding_model VARCHAR(100) NULL"))


def _add_missing_indexes_if_needed(sync_conn):
    """补齐设计文档要求的索引（旧库可能缺失）。CREATE INDEX IF NOT EXISTS 已存在时静默跳过。"""
    sync_conn.execute(text(
        "CREATE INDEX IF NOT EXISTS idx_sessions_parent ON chat_sessions(parent_session_key)"
    ))
    cols = _get_table_columns(sync_conn, "query_logs")
    if "search_app_id" in cols:
        sync_conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_query_logs_search_app ON query_logs(search_app_id)"
        ))


def _fix_kb_doc_data_sync(sync_conn):
    """
    修正 knowledge_bases 与 documents 表数据，使其与数据库设计文档及前端知识库/文档一览功能一致。
    """
    # 1. 同步 knowledge_bases.document_count
    sync_conn.execute(text("""
        UPDATE knowledge_bases
        SET document_count = (
            SELECT COUNT(*) FROM documents WHERE documents.knowledge_base_id = knowledge_bases.id
        )
    """))
    # 2. 同步 knowledge_bases.total_chunks（从 documents.chunk_count 汇总）
    sync_conn.execute(text("""
        UPDATE knowledge_bases
        SET total_chunks = (
            SELECT COALESCE(SUM(d.chunk_count), 0)
            FROM documents d
            WHERE d.knowledge_base_id = knowledge_bases.id
        )
    """))
    # 3. 补齐 knowledge_bases 默认值（icon/color 空则补默认）
    sync_conn.execute(text("""
        UPDATE knowledge_bases
        SET icon = CASE WHEN icon IS NULL OR icon = '' THEN '📚' ELSE icon END,
            color = CASE WHEN color IS NULL OR color = '' THEN '#667eea' ELSE color END
        WHERE icon IS NULL OR icon = '' OR color IS NULL OR color = ''
    """))
    sync_conn.execute(text("""
        UPDATE knowledge_bases
        SET chunk_size = COALESCE(chunk_size, 4096),
            chunk_overlap = COALESCE(chunk_overlap, 256),
            chunk_strategy = CASE WHEN chunk_strategy IS NULL OR chunk_strategy = '' THEN 'general' ELSE chunk_strategy END
        WHERE chunk_size IS NULL OR chunk_overlap IS NULL OR chunk_strategy IS NULL OR chunk_strategy = ''
    """))
    # 4. 修正 documents：非法 status 改为 pending
    sync_conn.execute(text("""
        UPDATE documents
        SET status = 'pending'
        WHERE status IS NULL OR status = '' OR status NOT IN ('pending','processing','completed','failed','uploaded')
    """))
    # 5. 修正 documents：file_size 空值补 0
    sync_conn.execute(text("""
        UPDATE documents SET file_size = 0 WHERE file_size IS NULL
    """))
    # 6. 修正 documents：tags 非合法 JSON 数组时置为 '[]'
    result = sync_conn.execute(text("SELECT id, tags FROM documents WHERE tags IS NOT NULL AND tags != ''"))
    for row in result:
        doc_id, tags_val = row[0], row[1]
        try:
            parsed = json.loads(tags_val) if isinstance(tags_val, str) else tags_val
            if not isinstance(parsed, list):
                sync_conn.execute(text("UPDATE documents SET tags = :val WHERE id = :id"), {"val": "[]", "id": doc_id})
        except (json.JSONDecodeError, TypeError):
            sync_conn.execute(text("UPDATE documents SET tags = :val WHERE id = :id"), {"val": "[]", "id": doc_id})


def _get_table_columns(sync_conn, table_name: str) -> list[str]:
    inspector = inspect(sync_conn)
    return [column["name"] for column in inspector.get_columns(table_name)]


def _run_column_migrations_sync():
    """SQLite 下同步执行 create_all 与列迁移（确保启动时关键列已存在）"""
    from .models import Base
    sync_url = _get_sync_database_url()
    sync_eng = create_engine(sync_url, poolclass=StaticPool, connect_args={"check_same_thread": False})
    with sync_eng.begin() as conn:
        Base.metadata.create_all(conn)
    with sync_eng.begin() as conn:
        _add_es_id_if_missing(conn)
        _backfill_es_id_if_empty(conn)
        _add_chunk_params_if_missing(conn)
        _add_embedding_model_if_missing(conn)
        _add_parent_session_key_if_missing(conn)
        _add_description_if_missing(conn)
        _add_query_logs_search_app_id_if_missing(conn)
        _add_missing_indexes_if_needed(conn)
        _fix_kb_doc_data_sync(conn)
    sync_eng.dispose()


async def init_db():
    """初始化数据库（创建表）并执行必要的列迁移"""
    from .models import Base
    # SQLite 先同步执行一次 create_all 与列迁移，避免启动时首个请求命中缺列
    if _is_sqlite_backend():
        _run_column_migrations_sync()
    eng, _ = init_engine()
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_add_es_id_if_missing)
        await conn.run_sync(_backfill_es_id_if_empty)
        await conn.run_sync(_add_chunk_params_if_missing)
        await conn.run_sync(_add_embedding_model_if_missing)
        await conn.run_sync(_add_parent_session_key_if_missing)
        await conn.run_sync(_add_description_if_missing)
        await conn.run_sync(_add_query_logs_search_app_id_if_missing)
        await conn.run_sync(_add_missing_indexes_if_needed)


async def close_db():
    """关闭数据库连接"""
    global engine
    if engine:
        await engine.dispose()
        engine = None
