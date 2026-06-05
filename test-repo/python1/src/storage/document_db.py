# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/5 16:57
# @Author  : cuils
# @Description:
sqlite数据库操作
"""
import json
from typing import Dict, List, Any


class DocumentDB:
    def __init__(self, db_path: str):
        import sqlite3
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def create(self) -> None:
        self.create_memory_table()
        self.create_document_table()

    def create_memory_table(self) -> None:
        """用于持久化存储对话历史"""
        sql = f"""
        CREATE TABLE IF NOT EXISTS rag_session_history (
        session_id TEXT PRIMARY KEY NOT NULL,
        epoch INTEGER,
        utterance TEXT,
        response TEXT,
        search_queries TEXT,
        ref_chunks TEXT,
        timestamp TEXT
        )
        """
        self.cursor.execute(sql)
        self.conn.commit()

    def create_document_table(self) -> None:
        """用于保存知识库文件信息"""
        sql = """
        CREATE TABLE IF NOT EXISTS knowledge_documents (
        doc_id TEXT PRIMARY KEY NOT NULL,
        index TEXT,
        filepath TEXT,
        filename TEXT,
        status TEXT,
        num_chunks INTEGER,
        timestamp TEXT
        )
        """
        self.cursor.execute(sql)
        self.conn.commit()

    def insert_memory(self, session_id, dialog_epochs: List[Dict[str, Any]]) -> None:
        """session_id, epoch, utterance, response, search_queries, ref_chunks, timestamp"""
        sql = f"""
        INSERT INTO rag_session_history VALUES(
        ?, ?, ?, ?, ?, ?, ?
        )
        """
        data = [
            [
                session_id,
                dialog_epoch.get("epoch"),
                dialog_epoch.get("utterance"),
                dialog_epoch.get("response"),
                json.dumps(dialog_epoch.get("search_queries"), ensure_ascii=False),
                json.dumps(dialog_epoch.get("ref_chunks"), ensure_ascii=False),
                dialog_epoch.get("timestamp")
            ]
            for dialog_epoch in dialog_epochs
        ]
        self.cursor.executemany(sql, data)
        self.conn.commit()

    def insert_document(self, **kwargs):
        """doc_id, index, filepath, filename, status, num_chunks, timestamp"""
        sql = f"""
        INSERT INTO knowledge_documents VALUES(
        ?, ?, ?, ?, ?, ?, ?
        )
        """
        data = [
            kwargs.get("doc_id"),
            kwargs.get("index"),
            kwargs.get("filepath"),
            kwargs.get("filename"),
            kwargs.get("status"),
            kwargs.get("num_chunks"),
            kwargs.get("timestamp")
        ]
        self.cursor.executemany(sql, [data])
        self.conn.commit()

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        sql = f"""
        SELECT * FROM rag_session_history
        WHERE session_id = "{session_id}"
        ORDER BY epoch
        """
        self.cursor.execute(sql)
        records = self.cursor.fetchall()
        dialog_epochs: List[Dict[str, Any]] = []
        for record in records:
            dialog_epoch = {
                "epoch": record[1],
                "utterance": record[2],
                "response": record[3],
                "search_queries": json.loads(record[4]) if record[4] else None,
                "ref_chunks": json.loads(record[5]) if record[5] else None,
                "timestamp": record[6]
            }
            dialog_epochs.append(dialog_epoch)
        return dialog_epochs

    def get_document_status(self, doc_id: str) -> Dict[str, Any]:
        """获取文档的状态

        """

    def update_file_status(self):
        """更新文件状态，这里主要是文件处理阶段使用的"""
        ...

    def delete(self):
        ...

    def close(self):
        self.cursor.close()
        self.conn.close()


class AsyncDocumentDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = None

    async def connect(self):
        import aiosqlite
        self.db = await aiosqlite.connect(self.db_path)

    async def create_table(self):
        """建表"""
        sql = f"""
        CREATE TABLE IF NOT EXISTS rag_session_history (
        session_id TEXT PRIMARY KEY NOT NULL,
        epoch INTEGER,
        utterance TEXT,
        response TEXT,
        search_queries TEXT,
        ref_chunks TEXT,
        timestamp TEXT
        )
        """
        await self.db.execute(sql)
        await self.db.commit()

    async def insert(self, session_id, dialog_epochs: List[Dict[str, Any]]) -> None:
        sql = f"""
        INSERT INTO rag_session_history VALUES(
        ?, ?, ?, ?, ?, ?, ?
        )
        """
        data = [
            [
                session_id,
                dialog_epoch.get("epoch"),
                dialog_epoch.get("utterance"),
                dialog_epoch.get("response"),
                json.dumps(dialog_epoch.get("search_queries"), ensure_ascii=False),
                json.dumps(dialog_epoch.get("ref_chunks"), ensure_ascii=False),
                dialog_epoch.get("timestamp")
            ]
            for dialog_epoch in dialog_epochs
        ]
        await self.db.executemany(sql, data)
        await self.db.commit()

    async def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        sql = f"""
        SELECT * FROM rag_session_history
        WHERE session_id = "{session_id}"
        ORDER BY epoch
        """
        cursor = await self.db.execute(sql)
        dialog_epochs: List[Dict[str, Any]] = []
        async for record in cursor:
            dialog_epoch = {
                "epoch": record[1],
                "utterance": record[2],
                "response": record[3],
                "search_queries": json.loads(record[4]) if record[4] else None,
                "ref_chunks": json.loads(record[5]) if record[5] else None,
                "timestamp": record[6]
            }
            dialog_epochs.append(dialog_epoch)
        return dialog_epochs

    async def update_file_status(self):
        pass

    async def delete(self):
        pass

    async def close(self):
        await self.db.close()