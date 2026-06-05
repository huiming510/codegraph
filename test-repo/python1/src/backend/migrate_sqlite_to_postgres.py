"""
将 SQLite 数据迁移到 PostgreSQL（异步）。

用法（在 src/backend 目录下执行）：
1) 设置源库路径（可选，默认 linkrag.db）
   - SQLITE_DATABASE=linkrag.db
2) 设置目标库 URL（必填）
   - DATABASE_URL=postgresql+asyncpg://postgres:password@127.0.0.1:5432/linkrag

命令：
    python migrate_sqlite_to_postgres.py
"""

import asyncio
import os
from sqlalchemy import select, insert, Integer, text
from sqlalchemy.ext.asyncio import create_async_engine

from database.models import Base


def _build_sqlite_url() -> str:
    db_name = os.environ.get("SQLITE_DATABASE", "linkrag.db")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = db_name if os.path.isabs(db_name) else os.path.join(script_dir, db_name)
    db_path = os.path.abspath(db_path).replace("\\", "/")
    return f"sqlite+aiosqlite:///{db_path}"


def _build_postgres_url() -> str:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("缺少 DATABASE_URL，请设置为 postgresql+asyncpg://...")
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if not database_url.startswith("postgresql+asyncpg://"):
        raise RuntimeError("DATABASE_URL 必须为 postgresql+asyncpg://... 或 postgresql://...")
    return database_url


def _quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


async def _reset_sequences(pg_conn):
    for table in Base.metadata.sorted_tables:
        pk_cols = [column for column in table.columns if column.primary_key and isinstance(column.type, Integer)]
        if not pk_cols:
            continue

        table_ref = _quote_ident(table.name)
        if table.schema:
            table_ref = f"{_quote_ident(table.schema)}.{table_ref}"

        for column in pk_cols:
            seq_name = (
                await pg_conn.execute(
                    text("SELECT pg_get_serial_sequence(:table_name, :column_name)"),
                    {"table_name": f"{table.schema}.{table.name}" if table.schema else table.name, "column_name": column.name},
                )
            ).scalar_one_or_none()
            if not seq_name:
                continue

            col_ref = _quote_ident(column.name)
            await pg_conn.execute(
                text(
                    f"""
                    SELECT setval(
                        :seq_name,
                        COALESCE((SELECT MAX({col_ref}) FROM {table_ref}), 1),
                        (SELECT COUNT(*) > 0 FROM {table_ref})
                    )
                    """
                ),
                {"seq_name": seq_name},
            )


async def migrate():
    sqlite_url = _build_sqlite_url()
    postgres_url = _build_postgres_url()

    sqlite_engine = create_async_engine(sqlite_url, echo=False)
    pg_engine = create_async_engine(postgres_url, echo=False)

    print(f"源 SQLite: {sqlite_url}")
    print(f"目标 PostgreSQL: {postgres_url}")

    try:
        async with pg_engine.begin() as pg_conn:
            await pg_conn.run_sync(Base.metadata.create_all)

        async with sqlite_engine.connect() as sqlite_conn, pg_engine.begin() as pg_conn:
            for table in reversed(Base.metadata.sorted_tables):
                await pg_conn.execute(table.delete())

            for table in Base.metadata.sorted_tables:
                rows = (await sqlite_conn.execute(select(table))).mappings().all()
                payload = [dict(row) for row in rows]
                if payload:
                    await pg_conn.execute(insert(table), payload)
                print(f"已迁移 {table.name}: {len(payload)} 条")

            await _reset_sequences(pg_conn)

        print("SQLite -> PostgreSQL 迁移完成")
    finally:
        await sqlite_engine.dispose()
        await pg_engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
