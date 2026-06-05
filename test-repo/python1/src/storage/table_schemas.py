# -*- coding: utf-8 -*-
"""
# @Time    : 2026/2/14 11:22
# @Author  : cuils
# @Description:
数据表结构定义
"""
from enum import Enum
from datetime import datetime
from sqlalchemy import String, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class FileStatus(Enum):
    COMPLETED = "completed" # 入库完成
    FAILED = "failed" # 入库失败
    PENDING = "pending" # 等待处理
    PROCESSING = "processing" # 正在处理
    UPLOADED = "uploaded" # 已上传，未处理


class Base(DeclarativeBase):
    # 创建时间
    create_time: Mapped[str] = mapped_column(String, default=now_str)
    # 最近更新时间
    last_update_time: Mapped[str] = mapped_column(String, default=now_str, onupdate=now_str)


class Document(Base):
    """文档表"""
    __tablename__ = "documents"
    doc_id: Mapped[str] = mapped_column(primary_key=True, autoincrement=False, nullable=False, comment="文档id")
    index: Mapped[str] = mapped_column(String(255), default="default", comment="文档所在索引")
    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="文件名")
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False, comment="文件保存路径")
    file_size: Mapped[int] = mapped_column(Integer, default=0, comment="文件大小")
    file_type: Mapped[str] = mapped_column(String(50), nullable=True, comment="文件类型 e.g. doc docx xls xlsx")
    status: Mapped[str] = mapped_column(String(20), default=FileStatus.PENDING.value, comment="文件处理状态")
    num_chunks: Mapped[int] = mapped_column(Integer, default=0, comment="文件分块数量")


class ChatSessionHistory(Base):
    """多轮对话历史"""
    __tablename__ = "chat_session_history"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, comment="主键id")
    session_id: Mapped[str] = mapped_column(String, nullable=False, comment="会话id，非主键id")
    epoch: Mapped[int] = mapped_column(Integer, default=0, comment="当前会话轮次")
    utterance: Mapped[str] = mapped_column(String(65535), nullable=False, comment="用户输入")
    response: Mapped[str] = mapped_column(String(65535), nullable=True, comment="模型回复")
    search_queries: Mapped[str] = mapped_column(String(65535), nullable=False, comment="搜索queries，json字符串")
    index: Mapped[str] = mapped_column(String(255), nullable=False, comment="搜索索引名称")
    ref_chunks: Mapped[str] = mapped_column(String(65535), nullable=False, comment="参考片段, json字符串")
    model_params: Mapped[str] = mapped_column(String(1024), nullable=False, comment="生成参数")
    search_params: Mapped[str] = mapped_column(String(1024), nullable=False, comment="搜索参数")
