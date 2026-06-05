"""数据库模型定义 - 多知识库架构"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, JSON, Index, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """基类"""
    pass


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nickname: Mapped[str] = mapped_column(String(50), default="用户")
    avatar: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="user")  # admin, user, guest
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    sessions: Mapped[List["ChatSession"]] = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    knowledge_bases: Mapped[List["KnowledgeBase"]] = relationship("KnowledgeBase", back_populates="creator")
    search_apps: Mapped[List["SearchApp"]] = relationship("SearchApp", back_populates="creator", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_users_role", "role"),
        Index("idx_users_active", "is_active"),
    )


class Permission(Base):
    """权限表"""
    __tablename__ = "permissions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index("idx_permissions_role_resource", "role", "resource"),
    )


class KnowledgeBase(Base):
    """知识库表"""
    __tablename__ = "knowledge_bases"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(50), default="📚")  # emoji图标
    color: Mapped[str] = mapped_column(String(20), default="#667eea")  # 主题色
    creator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否公开
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, default=0)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 使用的嵌入模型
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, archived
    es_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # 绑定的 ES 索引名，为空则用 linkrag_kb_{id}
    chunk_size: Mapped[int] = mapped_column(Integer, default=4096)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=256)
    chunk_strategy: Mapped[str] = mapped_column(String(50), default="general")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    creator: Mapped[Optional["User"]] = relationship("User", back_populates="knowledge_bases")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="knowledge_base", cascade="all, delete-orphan")
    sessions: Mapped[List["ChatSession"]] = relationship("ChatSession", back_populates="knowledge_base")
    
    __table_args__ = (
        Index("idx_kb_creator", "creator_id"),
        Index("idx_kb_status", "status"),
    )


class Document(Base):
    """文档表"""
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    file_type: Mapped[str] = mapped_column(String(50), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=True, index=True)
    tags: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, processing, completed, failed（uploaded 仅历史兼容）
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    knowledge_base: Mapped["KnowledgeBase"] = relationship("KnowledgeBase", back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_documents_kb", "knowledge_base_id"),
        Index("idx_documents_status", "status"),
        Index("idx_documents_created", "created_at"),
    )


class DocVirtualFolder(Base):
    """文档管理虚拟文件夹（层级仅用于展示，parent_key 为 kb-{id} 或 vf-{id}）"""
    __tablename__ = "doc_virtual_folders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # kb-{id} 或 vf-{id}
    kb_id: Mapped[int] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (Index("idx_doc_vf_parent_kb", "parent_key", "kb_id"),)


class DocFolderAssignment(Base):
    """文档归属文件夹：document_id -> parent_key（仅存非知识库根时，无记录表示在 kb 根下）"""
    __tablename__ = "doc_folder_assignments"

    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    parent_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # vf-{id} 或 kb-{id}

    __table_args__ = (Index("idx_doc_fa_parent", "parent_key"),)


class DocumentChunk(Base):
    """文档分块表"""
    __tablename__ = "document_chunks"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    extra_data: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关联
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    
    __table_args__ = (
        Index("idx_chunks_document", "document_id"),
        Index("idx_chunks_embedding", "embedding_id"),
    )


class ChatSession(Base):
    """会话表 - 关联知识库。app_ 开头为助手，conv_ 开头为对话（属于某助手）"""
    __tablename__ = "chat_sessions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    parent_session_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)  # 对话所属助手
    title: Mapped[str] = mapped_column(String(200), default="新对话")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 助手角色描述（app_ 时有效）
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    knowledge_base_id: Mapped[Optional[int]] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True)
    model_config: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # 模型配置 {provider, model, temperature}
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关联
    user: Mapped[Optional["User"]] = relationship("User", back_populates="sessions")
    knowledge_base: Mapped[Optional["KnowledgeBase"]] = relationship("KnowledgeBase", back_populates="sessions")
    messages: Mapped[List["ChatMessage"]] = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_sessions_user", "user_id"),
        Index("idx_sessions_kb", "knowledge_base_id"),
        Index("idx_sessions_parent", "parent_session_key"),
        Index("idx_sessions_updated", "updated_at"),
    )


class ChatMessage(Base):
    """消息表"""
    __tablename__ = "chat_messages"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extra_data: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    # 关联
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    
    __table_args__ = (
        Index("idx_messages_session", "session_id"),
        Index("idx_messages_created", "created_at"),
    )


class QueryLog(Base):
    """查询日志表 - 关联知识库与检索应用"""
    __tablename__ = "query_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    knowledge_base_id: Mapped[Optional[int]] = mapped_column(ForeignKey("knowledge_bases.id", ondelete="SET NULL"), nullable=True)
    search_app_id: Mapped[Optional[int]] = mapped_column(ForeignKey("search_apps.id", ondelete="SET NULL"), nullable=True)  # 检索应用ID
    query: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # 查询标题
    answer: Mapped[str] = mapped_column(Text, nullable=True)
    sources: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    model_config: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # 模型配置
    top_k: Mapped[int] = mapped_column(Integer, default=3)
    model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    success: Mapped[bool] = mapped_column(default=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    __table_args__ = (
        Index("idx_query_logs_kb", "knowledge_base_id"),
        Index("idx_query_logs_search_app", "search_app_id"),
        Index("idx_query_logs_user", "user_id"),
        Index("idx_query_logs_created", "created_at"),
        Index("idx_query_logs_success", "success"),
    )


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    module: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    __table_args__ = (
        Index("idx_system_logs_level_created", "level", "created_at"),
    )


class SearchApp(Base):
    """搜索应用表"""
    __tablename__ = "search_apps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # base64头像
    kb_ids: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)  # 知识库ID列表
    similarity_threshold: Mapped[float] = mapped_column(Float, default=0.2)
    vector_similarity_weight: Mapped[float] = mapped_column(Float, default=0.3)
    rerank_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    use_rerank: Mapped[bool] = mapped_column(Boolean, default=False)
    top_k: Mapped[int] = mapped_column(Integer, default=1024)
    summary: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.1)
    top_p: Mapped[float] = mapped_column(Float, default=0.3)
    presence_penalty: Mapped[float] = mapped_column(Float, default=0.4)
    frequency_penalty: Mapped[float] = mapped_column(Float, default=0.7)
    related_search: Mapped[bool] = mapped_column(Boolean, default=False)
    query_mindmap: Mapped[bool] = mapped_column(Boolean, default=False)
    search_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # dense, dense_filter, hybrid 等
    creator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 关联
    creator: Mapped[Optional["User"]] = relationship("User", back_populates="search_apps")

    __table_args__ = (
        Index("idx_search_apps_creator", "creator_id"),
        Index("idx_search_apps_created", "created_at"),
    )


class SystemConfig(Base):
    """系统配置表（key-value，用于 ES/解析服务等）"""
    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    config_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (Index("idx_system_config_key", "config_key"),)
