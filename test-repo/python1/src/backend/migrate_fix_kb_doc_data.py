"""
修正 knowledge_bases 与 documents 表数据，使其与数据库设计文档及前端知识库/文档一览功能一致。

修正内容：
1. knowledge_bases: 同步 document_count、total_chunks；补齐 chunk_size/chunk_overlap/chunk_strategy 默认值
2. documents: 确保 status 为合法值；tags 为合法 JSON 数组
3. knowledge_bases: icon、color 空值时补默认值

用法：在 backend 目录下执行  python migrate_fix_kb_doc_data.py
"""
import os
import json
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.environ.get("SQLITE_DATABASE", "linkrag.db")
DB_PATH = os.path.join(SCRIPT_DIR, DB_NAME) if not os.path.isabs(DB_NAME) else DB_NAME

# 文档 status 合法值（数据库设计文档）
VALID_DOC_STATUS = ("pending", "processing", "completed", "failed", "uploaded")


def migrate():
    if not os.path.exists(DB_PATH):
        print(f"数据库文件不存在: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()

        # ----- 1. 修正 knowledge_bases -----
        # 1.1 同步 document_count
        cur.execute("""
            UPDATE knowledge_bases
            SET document_count = (
                SELECT COUNT(*) FROM documents WHERE documents.knowledge_base_id = knowledge_bases.id
            )
        """)
        print(f"已同步 knowledge_bases.document_count，影响 {cur.rowcount} 条")

        # 1.2 同步 total_chunks（从 document_chunks 统计）
        try:
            cur.execute("""
                UPDATE knowledge_bases
                SET total_chunks = (
                    SELECT COALESCE(SUM(d.chunk_count), 0)
                    FROM documents d
                    WHERE d.knowledge_base_id = knowledge_bases.id
                )
            """)
            print(f"已同步 knowledge_bases.total_chunks，影响 {cur.rowcount} 条")
        except sqlite3.OperationalError as e:
            print(f"同步 total_chunks 跳过（可能无 document_chunks）: {e}")

        # 1.3 补齐默认值：icon, color, chunk_size, chunk_overlap, chunk_strategy
        cur.execute("""
            UPDATE knowledge_bases
            SET icon = COALESCE(NULLIF(TRIM(icon), ''), '📚'),
                color = COALESCE(NULLIF(TRIM(color), ''), '#667eea')
            WHERE icon IS NULL OR TRIM(icon) = '' OR color IS NULL OR TRIM(color) = ''
        """)
        print(f"已补齐 knowledge_bases icon/color 默认值，影响 {cur.rowcount} 条")

        cur.execute("""
            UPDATE knowledge_bases
            SET chunk_size = COALESCE(chunk_size, 4096),
                chunk_overlap = COALESCE(chunk_overlap, 256),
                chunk_strategy = COALESCE(NULLIF(TRIM(chunk_strategy), ''), 'general')
            WHERE chunk_size IS NULL OR chunk_overlap IS NULL OR chunk_strategy IS NULL OR TRIM(chunk_strategy) = ''
        """)
        print(f"已补齐 knowledge_bases 分块参数默认值，影响 {cur.rowcount} 条")

        # ----- 2. 修正 documents -----
        # 2.1 非法 status 改为 pending
        placeholders = ",".join("?" * len(VALID_DOC_STATUS))
        cur.execute(
            """
            UPDATE documents
            SET status = 'pending'
            WHERE status IS NULL OR status = '' OR status NOT IN (""" + placeholders + """)
            """,
            VALID_DOC_STATUS,
        )
        print(f"已修正 documents.status 非法值，影响 {cur.rowcount} 条")

        # 2.2 tags 为非合法 JSON 数组时置为 '[]'
        cur.execute("SELECT id, tags FROM documents WHERE tags IS NOT NULL AND tags != ''")
        rows = cur.fetchall()
        fixed_tags = 0
        for row in rows:
            tid, tags_val = row["id"], row["tags"]
            try:
                parsed = json.loads(tags_val)
                if not isinstance(parsed, list):
                    cur.execute("UPDATE documents SET tags = '[]' WHERE id = ?", (tid,))
                    fixed_tags += 1
            except (json.JSONDecodeError, TypeError):
                cur.execute("UPDATE documents SET tags = '[]' WHERE id = ?", (tid,))
                fixed_tags += 1
        print(f"已修正 documents.tags 格式，影响 {fixed_tags} 条")

        # 2.3 file_size 空值补 0
        cur.execute("UPDATE documents SET file_size = 0 WHERE file_size IS NULL")
        print(f"已补齐 documents.file_size 默认值，影响 {cur.rowcount} 条")

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("数据修正完成")


if __name__ == "__main__":
    migrate()
