"""
数据库迁移脚本 - SQLite
与 migrate_db 相同：根据当前模型确保所有表结构存在。
模型已包含 model_config、title 等字段，直接执行 init_db 即可。
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import init_engine
from database import init_db


async def migrate():
    """执行数据库初始化（表结构已包含 model_config 等字段）"""
    print("检查/更新数据库表结构（SQLite）...")
    init_engine()
    await init_db()
    print("完成。")
    from database import connection
    if connection.engine:
        await connection.engine.dispose()
        connection.engine = None
        connection.AsyncSessionLocal = None


if __name__ == "__main__":
    asyncio.run(migrate())
