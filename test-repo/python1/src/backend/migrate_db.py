"""
数据库迁移/初始化脚本 - SQLite
根据当前模型创建所有表（首次运行或空库时使用）
"""
import asyncio
import sys
import os

# 确保 backend 目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import init_engine
from database import init_db


async def migrate():
    """执行数据库初始化（创建所有表）"""
    print("开始数据库初始化（SQLite）...")
    init_engine()
    await init_db()
    print("数据库表创建完成。可启动应用，应用启动时会自动初始化默认权限与默认知识库。")
    from database import connection
    if connection.engine:
        await connection.engine.dispose()
        connection.engine = None
        connection.AsyncSessionLocal = None


if __name__ == "__main__":
    asyncio.run(migrate())
