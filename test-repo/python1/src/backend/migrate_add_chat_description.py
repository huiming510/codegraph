"""
为 chat_sessions 表添加 description 列（助手角色描述），并将 model_config 中已有的 description 迁移到该列。
用法：在 backend 目录下执行  python migrate_add_chat_description.py
"""
import json
import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.environ.get("SQLITE_DATABASE", "linkrag.db")
DB_PATH = os.path.join(SCRIPT_DIR, DB_NAME) if not os.path.isabs(DB_NAME) else DB_NAME


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute("PRAGMA table_info(chat_sessions)")
        columns = [row[1] for row in cur.fetchall()]
        if "description" not in columns:
            conn.execute("ALTER TABLE chat_sessions ADD COLUMN description TEXT NULL")
            conn.commit()
            print("已添加 chat_sessions.description 列")
        else:
            print("chat_sessions.description 已存在，跳过")

        # 将 model_config 中的 description 迁移到 description 列（仅 app_ 且 description 列为空）
        cur = conn.execute(
            "SELECT id, session_key, model_config, description FROM chat_sessions "
            "WHERE session_key LIKE 'app_%' AND parent_session_key IS NULL"
        )
        rows = cur.fetchall()
        migrated = 0
        for row in rows:
            rid, session_key, mc_json, desc_col = row
            if desc_col:
                continue
            if not mc_json:
                continue
            try:
                mc = json.loads(mc_json) if isinstance(mc_json, str) else mc_json
                desc = mc.get("description") if mc else None
                if desc:
                    conn.execute("UPDATE chat_sessions SET description = ? WHERE id = ?", (desc, rid))
                    migrated += 1
            except (json.JSONDecodeError, TypeError):
                pass
        if migrated:
            conn.commit()
            print(f"已迁移 {migrated} 条记录的 description 从 model_config 到 description 列")
    finally:
        conn.close()
    print("迁移完成")


if __name__ == "__main__":
    migrate()
