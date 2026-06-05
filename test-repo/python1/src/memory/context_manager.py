# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/6 10:03
# @Author  : cuils
# @Description:
"""
import json
from datetime import datetime

from pydantic import BaseModel
from cachetools import LRUCache
from typing import List, Dict, Any, Optional
from src.storage import ContextPersistent, ChatSessionHistory


class DialogEpoch(BaseModel):
    epoch: int  # 对话轮次
    utterance: str  # 用户输入
    response: str  # 模型输出
    search_queries: List[str] = []  # 检索query
    index: str
    ref_chunks: List[str] = []  # 参考片段
    model_params: Optional[Dict[str, Any]] = None
    search_params: Optional[Dict[str, Any]] = None


class ContextManager:
    def __init__(self, cache_size: int = 100, persistent: ContextPersistent = None):
        self.sessions: Dict[str, List[DialogEpoch]] = LRUCache(maxsize=cache_size)
        self.persistent = persistent

    async def from_persistent(self, session_id: str) -> List[DialogEpoch]:
        """从数据库获取db"""
        _persistent_epochs: List[ChatSessionHistory] = await self.persistent.get_history(session_id)
        history_epochs = []
        for _persistent_epoch in _persistent_epochs:
            dialog_epoch = DialogEpoch(
                epoch=_persistent_epoch.epoch,
                utterance=_persistent_epoch.utterance,
                response=_persistent_epoch.response,
                search_queries=json.loads(_persistent_epoch.search_queries),
                index=_persistent_epoch.index,
                ref_chunks=json.loads(_persistent_epoch.ref_chunks)
            )
            if _persistent_epoch.model_params:
                dialog_epoch.model_params = json.loads(_persistent_epoch.model_params)
            if _persistent_epoch.search_params:
                dialog_epoch.search_params = json.loads(_persistent_epoch.search_params)
            history_epochs.append(dialog_epoch)
        return history_epochs

    async def get_history(self, session_id: str) -> List[DialogEpoch]:
        """从LRU临时缓存中获取对话历史，若LRU中不存在，则再从db获取对话历史
        仅返回历史五轮对话，第一轮以及后四轮
        """
        history_epochs = self.sessions.get(session_id)
        if not history_epochs:
            # 读db
            history_epochs = await self.from_persistent(session_id)

            # 写cache
            self.sessions[session_id] = history_epochs

        if not history_epochs:
            return []

        if len(history_epochs) <= 5:
            return history_epochs
        return history_epochs[:1] + history_epochs[-4:]

    async def set_history(self, session_id: str, dialog_epoch: DialogEpoch):
        """保存当前对话
        若当前对话信息存在LRU缓存中，将当前轮次对话直接添加到history中，并保存之db
        若当前对话信息在LRU缓存中不存在，需要先将对话历史恢复到LRU缓存中，然后在添加保存
        """
        if session_id in self.sessions:
            # 写cache
            self.sessions[session_id].append(dialog_epoch)
            # 写db
            await self.persistent.insert_history(session_id, **dialog_epoch.model_dump())

        else:
            # 读db
            history_epochs = await self.from_persistent(session_id)
            # 写cache
            self.sessions[session_id] = history_epochs
            self.sessions[session_id].append(dialog_epoch)
            # 写db
            await self.persistent.insert_history(session_id, **dialog_epoch.model_dump())
