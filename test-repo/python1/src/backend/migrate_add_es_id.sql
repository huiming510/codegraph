-- 为 knowledge_bases 表添加 es_id 列（仅当不存在时需执行一次）
-- 用法：sqlite3 linkrag.db "ALTER TABLE knowledge_bases ADD COLUMN es_id VARCHAR(100) NULL;"
-- 若已存在 es_id 列，再次执行会报错，可忽略。
ALTER TABLE knowledge_bases ADD COLUMN es_id VARCHAR(100) NULL;
