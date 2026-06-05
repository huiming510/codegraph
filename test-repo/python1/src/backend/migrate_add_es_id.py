"""
为 knowledge_bases 表添加 es_id 字段（用于与 ES 索引绑定）。
仅当列不存在时执行 ALTER TABLE。仅依赖 Python 内置 sqlite3，无需安装依赖。
用法：在 backend 目录下执行  python migrate_add_es_id.py
"""
import os
import sqlite3

# 数据库路径：当前脚本所在目录下的 linkrag.db，或通过环境变量 SQLITE_DATABASE 指定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.environ.get("SQLITE_DATABASE", "linkrag.db")
DB_PATH = os.path.join(SCRIPT_DIR, DB_NAME) if not os.path.isabs(DB_NAME) else DB_NAME


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("PRAGMA table_info(knowledge_bases)")
        columns = [row[1] for row in cur.fetchall()]
        if "es_id" not in columns:
            conn.execute("ALTER TABLE knowledge_bases ADD COLUMN es_id VARCHAR(100) NULL")
            conn.commit()
            print("已添加 knowledge_bases.es_id 列")
        else:
            print("knowledge_bases.es_id 已存在，跳过")
    finally:
        conn.close()
    print("迁移完成")


if __name__ == "__main__":
    migrate()
