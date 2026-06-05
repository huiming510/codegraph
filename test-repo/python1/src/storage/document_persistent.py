# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/14 14:31
# @Author  : cuils
# @Description:
文档持久化
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select, update, delete
from .table_schemas import Document, FileStatus


class DocumentPersistent:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def insert_document(
        self,
        doc_id: str,
        index: str,
        filename: str,
        file_path: str,
        **kwargs
    ) -> None:
        """创建文档"""
        async with self.session_factory() as session:
            try:
                document = Document(
                    doc_id=doc_id,
                    index=index,
                    filename=filename,
                    file_path=file_path,
                    file_size=kwargs.get("file_size"),
                    file_type=kwargs.get("file_type")
                )
                session.add(document)
                await session.flush()
                await session.refresh(document)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_document(self, doc_id: str) -> Optional[Document]:
        """获取单个文档"""
        async with self.session_factory() as session:
            result = await session.execute(select(Document).where(Document.doc_id == doc_id))
            return result.scalar_one_or_none()

    async def get_documents_from_index(
        self,
        index: str,
        skip: int = 0,
        limit: int = 100,
        status: Optional[FileStatus] = None,
        regex: Optional[str] = None,
    ) -> List[Document]:
        """获取某个索引的文档"""
        async with self.session_factory() as session:
            sql = select(Document).where(Document.index == index).order_by(Document.create_time.desc())
            if status:
                sql = sql.where(Document.status == status.value)
            if regex:
                sql = sql.where(Document.filename.ilike(f"%{regex.strip()}%"))
            sql = sql.offset(skip).limit(limit)
            result = await session.execute(sql)
            return list(result.scalars().all())

    async def update_document(self, doc_id: str, status: FileStatus, num_chunks: Optional[int] = None) -> None:
        """更新文档状态和分块数量"""
        async with self.session_factory() as session:
            changes = {
                "status": status.value,
                "last_update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            if num_chunks:
                changes["num_chunks"] = num_chunks
            try:
                await session.execute(update(Document).where(Document.doc_id == doc_id).values(**changes))
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def delete_document(self, doc_id: str) -> None:
        """删除文档"""
        async with self.session_factory() as session:
            try:
                await session.execute(delete(Document).where(Document.doc_id == doc_id))
                await session.commit()
            except Exception:
                await session.rollback()
                raise
