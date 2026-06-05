# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/14 15:17
# @Author  : cuils
# @Description:
对话上下文持久化
"""
import json
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from .table_schemas import ChatSessionHistory


class ContextPersistent:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def insert_history(
        self,
        session_id: str,
        epoch: int,
        utterance: str,
        response: Optional[str],
        search_queries: List[str],
        index: str,
        ref_chunks: List[str],
        model_params: Optional[Dict[str, Any]] = None,
        search_params: Optional[Dict[str, Any]] = None
    ) -> None:
        async with self.session_factory() as session:
            try:
                history = ChatSessionHistory(
                    session_id=session_id,
                    epoch=epoch,
                    utterance=utterance,
                    response=response,
                    search_queries=json.dumps(search_queries, ensure_ascii=False),
                    index=index,
                    ref_chunks=json.dumps(ref_chunks, ensure_ascii=False),
                    model_params=json.dumps(model_params, ensure_ascii=False) if model_params is not None else None,
                    search_params=json.dumps(search_params, ensure_ascii=False) if search_params is not None else None
                )
                session.add(history)
                await session.flush()
                await session.refresh(history)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_history(self, session_id: str) -> List[ChatSessionHistory]:
        """获取某个会话对话历史"""
        async with self.session_factory() as session:
            query = select(ChatSessionHistory).where(ChatSessionHistory.session_id == session_id).order_by(
                ChatSessionHistory.epoch.asc())
            result = await session.execute(query)
            return list(result.scalars().all())

    async def delete_history(self, session_id: str, epoch: Optional[int] = None, op: Optional[str] = None) -> None:
        """删除对话历史"""
        async with self.session_factory() as session:
            query = delete(ChatSessionHistory).where(ChatSessionHistory.session_id == session_id)
            if epoch and op:
                if op == "lt":
                    query = query.where(ChatSessionHistory.epoch < epoch)
                elif op == "gt":
                    query = query.where(ChatSessionHistory.epoch > epoch)
                elif op == "eq":
                    query = query.where(ChatSessionHistory.epoch == epoch)
                else:
                    raise ValueError("op must be 'lt' or 'gt' or 'eq'")
            try:
                await session.execute(query)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def update_history(self) -> None:
        """对话历史不需要修改"""
        pass