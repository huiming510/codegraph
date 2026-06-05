"""数据库CRUD操作 - 多知识库架构"""
from datetime import datetime
import uuid
from typing import Optional, List
from sqlalchemy import select, update, delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import hashlib

# 系统角色常量（与 users.role 一致，用于权限与菜单）
# 管理员=团队leader；user=开发人员；guest=用户（仅检索、聊天）
ROLE_ADMIN = "admin"
ROLE_DEVELOPER = "user"   # 开发人员：知识库创建/更新、文档上传、检索聊天
ROLE_USER = "guest"       # 用户：检索、聊天
ROLE_LABELS = {"admin": "管理员", "user": "开发人员", "guest": "用户"}

from .models import (
    Document, DocumentChunk, ChatSession, ChatMessage,
    QueryLog, SystemLog, SystemConfig, User, Permission, KnowledgeBase,
    DocVirtualFolder, DocFolderAssignment, SearchApp,
)


# ==================== User CRUD ====================

def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    return hash_password(password) == password_hash


async def create_user(
    db: AsyncSession,
    username: str,
    password: str,
    email: str = None,
    nickname: str = None,
    role: str = "user",
) -> User:
    """创建用户"""
    user = User(
        username=username,
        password_hash=hash_password(password),
        email=email,
        nickname=nickname or username,
        role=role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """根据ID获取用户"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> Optional[User]:
    """根据用户名获取用户"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def get_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    role: str = None,
    is_active: bool = None,
) -> List[User]:
    """获取用户列表"""
    query = select(User).order_by(User.created_at.desc())
    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_user(db: AsyncSession, user_id: int, **kwargs):
    """更新用户"""
    kwargs["updated_at"] = datetime.now()
    await db.execute(update(User).where(User.id == user_id).values(**kwargs))


async def update_user_password(db: AsyncSession, user_id: int, new_password: str):
    """更新用户密码"""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(password_hash=hash_password(new_password), updated_at=datetime.now())
    )


async def update_user_last_login(db: AsyncSession, user_id: int):
    """更新最后登录时间"""
    await db.execute(update(User).where(User.id == user_id).values(last_login=datetime.now()))


async def delete_user(db: AsyncSession, user_id: int):
    """删除用户"""
    await db.execute(delete(User).where(User.id == user_id))


async def count_users(db: AsyncSession, role: str = None) -> int:
    """统计用户数量"""
    query = select(func.count(User.id))
    if role:
        query = query.where(User.role == role)
    result = await db.execute(query)
    return result.scalar() or 0


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """验证用户登录"""
    user = await get_user_by_username(db, username)
    if not user or not verify_password(password, user.password_hash) or not user.is_active:
        return None
    return user


def get_full_menu_list():
    """完整菜单结构（与前端约定一致），返回 (base_menus, system_menu)。用于 auth/menu 按角色过滤。"""
    # 导航顺序：首页 | 智能问答 | 工作流 | 知识库 | 智能检索 | 文档管理 | 系统设置
    # 角色与菜单：管理员=全部；开发人员(user)=全部 base；用户(guest)=仅首页、智能问答、智能检索
    base = [
        {
            "path": "/home",
            "name": "home",
            "component": "/home/index",
            "meta": {"icon": "HomeOutlined", "title": "首页", "isLink": "", "isHide": False, "isFull": False, "isAffix": True, "isKeepAlive": True},
        },
        {
            "path": "/chat",
            "name": "chatMenu",
            "redirect": "/chat/list",
            "meta": {"icon": "CommentOutlined", "title": "智能问答", "isLink": "", "isHide": False, "isFull": False, "isAffix": False, "isKeepAlive": True},
            "children": [
                {"path": "/chat/list", "name": "chatList", "component": "/chat/list/index", "meta": {"icon": "MessageOutlined", "title": "AI 对话", "isLink": "", "isHide": True, "isFull": False, "hideMenu": True, "isAffix": False, "isKeepAlive": True}},
                {"path": "/chat/detail", "name": "chatDetail", "component": "/chat/detail/index", "meta": {"icon": "MessageOutlined", "title": "对话详情", "isLink": "", "isHide": True, "isFull": False, "hideMenu": True, "isAffix": False, "isKeepAlive": False}},
            ],
        },
        # {
        #     "path": "/workflow",
        #     "name": "workflow",
        #     "component": "/workflow/index",
        #     "meta": {"icon": "ApartmentOutlined", "title": "工作流", "isLink": "", "isHide": False, "isFull": False, "isAffix": False, "isKeepAlive": True},
        # },
        {
            "path": "/knowledge",
            "name": "knowledge",
            "redirect": "/knowledge/knowledgeMgt",
            "meta": {"icon": "FolderOutlined", "title": "知识库", "isLink": "", "isHide": False, "isFull": False, "isAffix": False, "isKeepAlive": True},
            "children": [
                {"path": "/knowledge/knowledgeMgt", "name": "knowledgeMgt", "component": "/knowledge/knowledgeMgt/index", "meta": {"icon": "icon-knowledge", "title": "知识库管理", "isLink": "", "isHide": True, "isFull": False, "isAffix": False, "isKeepAlive": True}},
                {"path": "/knowledge/documentMgt", "name": "documentMgt", "component": "/knowledge/documentMgt/index", "meta": {"icon": "icon-docs-knowledge", "title": "文档管理", "isLink": "", "isHide": True, "isFull": False, "isAffix": False, "isKeepAlive": True}},
            ],
        },
        {
            "path": "/query",
            "name": "query",
            "component": "/query/index",
            "meta": {"icon": "SearchOutlined", "title": "智能检索", "isLink": "", "isHide": False, "isFull": False, "isAffix": False, "isKeepAlive": True},
        },
        # {
        #     "path": "/AllDocumentMgt",
        #     "name": "allDocumentMgt",
        #     "component": "/AllDocumentMgt/index",
        #     "meta": {"icon": "FolderOutlined", "title": "文档管理", "isLink": "", "isHide": False, "isFull": False, "isAffix": False, "isKeepAlive": True},
        # },
    ]
    system_menu = {
        "path": "/system",
        "name": "system",
        "redirect": "/system/userMgt",
        "meta": {"icon": "SettingOutlined", "title": "系统设置", "isLink": "", "isHide": False, "isFull": False, "isAffix": False, "isKeepAlive": True},
        "children": [
            {"path": "/system/userMgt", "name": "userMgt", "component": "/system/userMgt/index", "meta": {"icon": "icon-accountMgt", "title": "用户管理", "isLink": "", "isHide": False, "isFull": False, "isAffix": False, "isKeepAlive": True}},
            {"path": "/system/llmConfig", "name": "llmConfig", "component": "/system/llmConfig/index", "meta": {"icon": "icon-modelConfig", "title": "模型配置", "isLink": "", "isHide": False, "isFull": False, "isAffix": False, "isKeepAlive": True}},
            {"path": "/system/esConfig", "name": "esConfig", "component": "/system/esConfig/index", "meta": {"icon": "icon-companyMgt", "title": "ES环境配置", "isLink": "", "isHide": False, "isFull": False, "isAffix": False, "isKeepAlive": True}},
            {"path": "/system/logs", "name": "logs", "component": "/system/logs/index", "meta": {"icon": "icon-systemLog", "title": "系统日志", "isLink": "", "isHide": False, "isFull": False, "isAffix": False, "isKeepAlive": True}},
        ],
    }
    return base, system_menu


# 用户(guest)仅可访问的 base 菜单 name 列表：首页、智能问答、智能检索
MENU_NAMES_FOR_GUEST = ("home", "chatMenu", "query")


def get_menus_for_role(role: str) -> list:
    """
    按角色返回可访问的菜单列表。用于鉴权中心与前端动态路由。
    - admin：全部 base + 系统设置（用户管理、模型配置、ES、日志）
    - user（开发人员）：全部 base（含工作流、知识库、文档管理）
    - guest（用户）：仅首页、智能问答、智能检索
    """
    base_menus, system_menu = get_full_menu_list()
    if role == ROLE_ADMIN:
        return base_menus + [system_menu]
    if role == ROLE_USER:
        return [m for m in base_menus if m.get("name") in MENU_NAMES_FOR_GUEST]
    # user（开发人员）及其他：全部 base，无系统设置
    return base_menus


# ==================== Permission CRUD ====================

async def create_permission(db: AsyncSession, role: str, resource: str, action: str) -> Permission:
    """创建权限"""
    perm = Permission(role=role, resource=resource, action=action)
    db.add(perm)
    await db.flush()
    return perm


async def check_permission(db: AsyncSession, role: str, resource: str, action: str) -> bool:
    """检查权限"""
    result = await db.execute(
        select(Permission)
        .where(Permission.role == role, Permission.resource == resource, Permission.action == action)
    )
    return result.scalar_one_or_none() is not None


async def get_permissions(
    db: AsyncSession,
    role: str = None,
    skip: int = 0,
    limit: int = 200,
) -> List[Permission]:
    """获取权限列表（可选按角色筛选）"""
    query = select(Permission).order_by(Permission.role, Permission.resource, Permission.action)
    if role:
        query = query.where(Permission.role == role)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def init_default_permissions(db: AsyncSession):
    """
    初始化默认权限（鉴权中心）。
    管理员：用户增删改查、审批入库、知识库发布、模型API、日志等全部权限。
    开发人员(user)：文档上传/处理、知识库创建更新(开发模式)、检索与聊天。
    用户(guest)：仅检索、聊天。
    """
    default_permissions = [
        # 管理员：全部
        ("admin", "documents", "read"), ("admin", "documents", "write"), ("admin", "documents", "delete"),
        ("admin", "chat", "read"), ("admin", "chat", "write"),
        ("admin", "query", "read"), ("admin", "query", "write"),
        ("admin", "logs", "read"), ("admin", "users", "read"), ("admin", "users", "write"), ("admin", "users", "delete"),
        ("admin", "knowledge_base", "read"), ("admin", "knowledge_base", "write"), ("admin", "knowledge_base", "delete"),
        # 开发人员：文档、对话、检索、知识库读写（无用户/日志管理）
        ("user", "documents", "read"), ("user", "documents", "write"),
        ("user", "chat", "read"), ("user", "chat", "write"),
        ("user", "query", "read"), ("user", "query", "write"),
        ("user", "knowledge_base", "read"), ("user", "knowledge_base", "write"),
        # 用户(guest)：仅检索、聊天（只读文档与知识库）
        ("guest", "documents", "read"), ("guest", "chat", "read"), ("guest", "chat", "write"),
        ("guest", "query", "read"), ("guest", "knowledge_base", "read"),
    ]
    for role, resource, action in default_permissions:
        if not await check_permission(db, role, resource, action):
            await create_permission(db, role, resource, action)
    await db.commit()


# ==================== KnowledgeBase CRUD ====================

def build_default_es_id(kb_id: int) -> str:
    """生成知识库默认 ES 索引名（带短随机后缀，降低冲突风险）。"""
    suffix = uuid.uuid4().hex[:8]
    return f"linkrag_kb_{kb_id}_{suffix}"


async def get_knowledge_base_by_es_id(db: AsyncSession, es_id: str) -> Optional[KnowledgeBase]:
    """按 es_id 获取知识库（精确匹配）。"""
    normalized = (es_id or "").strip()
    if not normalized:
        return None
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.es_id == normalized))
    return result.scalar_one_or_none()


async def get_knowledge_base_by_name(db: AsyncSession, name: str) -> Optional[KnowledgeBase]:
    """按名称获取知识库（精确匹配）。"""
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.name == name))
    return result.scalars().first()


async def create_knowledge_base(
    db: AsyncSession,
    name: str,
    description: str = None,
    icon: str = "📚",
    color: str = "#667eea",
    creator_id: int = None,
    is_public: bool = True,
    es_id: str = None,
    chunk_size: int = 4096,
    chunk_overlap: int = 256,
    chunk_strategy: str = "general",
) -> KnowledgeBase:
    """创建知识库"""
    normalized_es_id = (es_id or "").strip() or None
    kb = KnowledgeBase(
        name=name,
        description=description,
        icon=icon,
        color=color,
        creator_id=creator_id,
        is_public=is_public,
        es_id=normalized_es_id,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunk_strategy=(chunk_strategy or "general").strip() or "general",
    )
    db.add(kb)
    await db.flush()
    if not kb.es_id:
        kb.es_id = build_default_es_id(kb.id)
        await db.flush()
    await db.refresh(kb)
    return kb


async def get_knowledge_base(db: AsyncSession, kb_id: int) -> Optional[KnowledgeBase]:
    """获取知识库"""
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    return result.scalar_one_or_none()


async def get_knowledge_bases(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    creator_id: int = None,
    is_public: bool = None,
    status: str = "active",
) -> List[KnowledgeBase]:
    """获取知识库列表"""
    query = select(KnowledgeBase).order_by(KnowledgeBase.created_at.desc())
    if creator_id:
        query = query.where(KnowledgeBase.creator_id == creator_id)
    if is_public is not None:
        query = query.where(KnowledgeBase.is_public == is_public)
    if status:
        query = query.where(KnowledgeBase.status == status)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_knowledge_base(db: AsyncSession, kb_id: int, **kwargs):
    """更新知识库"""
    kwargs["updated_at"] = datetime.now()
    await db.execute(update(KnowledgeBase).where(KnowledgeBase.id == kb_id).values(**kwargs))


async def update_kb_document_count(db: AsyncSession, kb_id: int):
    """更新知识库文档数量"""
    count_result = await db.execute(
        select(func.count(Document.id)).where(Document.knowledge_base_id == kb_id)
    )
    count = count_result.scalar() or 0
    await db.execute(
        update(KnowledgeBase).where(KnowledgeBase.id == kb_id).values(document_count=count, updated_at=datetime.now())
    )


async def delete_knowledge_base(db: AsyncSession, kb_id: int):
    """删除知识库及其下所有文档、文档分块表数据及虚拟文件夹树"""
    # 先删除该知识库下所有文档的分块（document_chunks）
    subq = select(Document.id).where(Document.knowledge_base_id == kb_id)
    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id.in_(subq)))
    # 再删除该知识库下所有文档（documents）
    await db.execute(delete(Document).where(Document.knowledge_base_id == kb_id))
    # 同时删除该知识库下的虚拟文件夹树（虚拟文件夹本身；文档归属记录依赖 document_id 已随文档级联删除）
    await db.execute(delete(DocVirtualFolder).where(DocVirtualFolder.kb_id == kb_id))
    # 最后删除知识库
    await db.execute(delete(KnowledgeBase).where(KnowledgeBase.id == kb_id))


async def count_knowledge_bases(db: AsyncSession, status: str = "active") -> int:
    """统计知识库数量"""
    query = select(func.count(KnowledgeBase.id))
    if status:
        query = query.where(KnowledgeBase.status == status)
    result = await db.execute(query)
    return result.scalar() or 0


# ==================== Document CRUD ====================

async def create_document(
    db: AsyncSession,
    knowledge_base_id: int,
    filename: str,
    file_path: str,
    file_size: int = 0,
    file_type: str = None,
    tags: List[str] = None,
    content_hash: str = None,
) -> Document:
    """创建文档"""
    doc = Document(
        knowledge_base_id=knowledge_base_id,
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        file_type=file_type,
        tags=tags or [],
        content_hash=content_hash,
        status="pending",
    )
    db.add(doc)
    await db.flush()
    await db.refresh(doc)
    return doc


async def get_document(db: AsyncSession, doc_id: int) -> Optional[Document]:
    """获取单个文档"""
    result = await db.execute(select(Document).where(Document.id == doc_id))
    return result.scalar_one_or_none()


async def get_document_by_id(db: AsyncSession, doc_id: int) -> Optional[Document]:
    """根据ID获取文档（别名）"""
    return await get_document(db, doc_id)


async def get_document_by_hash(db: AsyncSession, content_hash: str, kb_id: int = None) -> Optional[Document]:
    """根据内容哈希获取文档"""
    query = select(Document).where(Document.content_hash == content_hash)
    if kb_id:
        query = query.where(Document.knowledge_base_id == kb_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_documents(
    db: AsyncSession,
    knowledge_base_id: int = None,
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    search: str = None,
) -> List[Document]:
    """获取文档列表"""
    query = select(Document).order_by(Document.created_at.desc())
    if knowledge_base_id:
        query = query.where(Document.knowledge_base_id == knowledge_base_id)
    if status:
        query = query.where(Document.status == status)
    if search:
        query = query.where(Document.filename.ilike(f"%{search.strip()}%"))
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_document_status(db: AsyncSession, doc_id: int, status: str, chunk_count: int = None):
    """更新文档状态"""
    values = {"status": status, "updated_at": datetime.now()}
    if chunk_count is not None:
        values["chunk_count"] = chunk_count
    await db.execute(update(Document).where(Document.id == doc_id).values(**values))


async def delete_document(db: AsyncSession, doc_id: int):
    """删除文档"""
    await db.execute(delete(Document).where(Document.id == doc_id))


async def count_documents(db: AsyncSession, knowledge_base_id: int = None, status: str = None) -> int:
    """统计文档数量"""
    query = select(func.count(Document.id))
    if knowledge_base_id:
        query = query.where(Document.knowledge_base_id == knowledge_base_id)
    if status:
        query = query.where(Document.status == status)
    result = await db.execute(query)
    return result.scalar() or 0


# ==================== DocVirtualFolder & DocFolderAssignment CRUD ====================

async def get_virtual_folders(db: AsyncSession, kb_id: int = None) -> List[DocVirtualFolder]:
    """获取虚拟文件夹列表，可选按知识库筛选"""
    query = select(DocVirtualFolder).order_by(DocVirtualFolder.created_at.asc())
    if kb_id is not None:
        query = query.where(DocVirtualFolder.kb_id == kb_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_virtual_folder(
    db: AsyncSession,
    id: str,
    name: str,
    parent_key: str,
    kb_id: int,
) -> DocVirtualFolder:
    """创建虚拟文件夹"""
    vf = DocVirtualFolder(id=id, name=name, parent_key=parent_key, kb_id=kb_id)
    db.add(vf)
    await db.flush()
    await db.refresh(vf)
    return vf


async def get_virtual_folder(db: AsyncSession, vf_id: str) -> Optional[DocVirtualFolder]:
    """按 id 获取虚拟文件夹"""
    result = await db.execute(select(DocVirtualFolder).where(DocVirtualFolder.id == vf_id))
    return result.scalar_one_or_none()


async def _collect_vf_ids_under(db: AsyncSession, parent_key: str) -> set:
    """递归收集 parent_key 下所有虚拟文件夹的 vf- id（含自身 key 中的 id）"""
    result = await db.execute(select(DocVirtualFolder.id).where(DocVirtualFolder.parent_key == parent_key))
    ids = set()
    for (cid,) in result.all():
        key = f"vf-{cid}"
        ids.add(key)
        ids.update(await _collect_vf_ids_under(db, key))
    return ids


async def get_document_ids_in_virtual_folder_tree(db: AsyncSession, vf_id: str) -> List[int]:
    """
    获取某虚拟文件夹及其所有子孙文件夹内的文档 id 列表（用于删除文件夹时一并删除这些文档）。
    """
    vf = await get_virtual_folder(db, vf_id)
    if not vf:
        return []
    to_remove_keys = await _collect_vf_ids_under(db, f"vf-{vf_id}")
    to_remove_keys.add(f"vf-{vf_id}")
    if not to_remove_keys:
        return []
    result = await db.execute(
        select(DocFolderAssignment.document_id).where(DocFolderAssignment.parent_key.in_(to_remove_keys))
    )
    return [row[0] for row in result.all()]


async def delete_virtual_folder(db: AsyncSession, vf_id: str) -> Optional[int]:
    """
    删除虚拟文件夹（含所有子孙），并将归属该文件夹及其子孙的文档改回知识库根。
    返回被删除的文件夹数量。
    """
    vf = await get_virtual_folder(db, vf_id)
    if not vf:
        return None
    kb_id = vf.kb_id
    kb_key = f"kb-{kb_id}"
    to_remove_keys = await _collect_vf_ids_under(db, f"vf-{vf_id}")
    to_remove_keys.add(f"vf-{vf_id}")
    # 删除归属到这些文件夹的文档记录（无记录表示在知识库根）
    for pk in to_remove_keys:
        await db.execute(delete(DocFolderAssignment).where(DocFolderAssignment.parent_key == pk))
    # 删除所有虚拟文件夹（id 列表）
    vf_ids = [k.replace("vf-", "") for k in to_remove_keys]
    for vid in vf_ids:
        await db.execute(delete(DocVirtualFolder).where(DocVirtualFolder.id == vid))
    return len(vf_ids)


async def get_folder_assignments(db: AsyncSession, knowledge_base_id: int = None) -> dict:
    """
    返回 document_id -> parent_key 的映射。
    仅包含有记录的文档（在虚拟文件夹内的）；未在表中的文档前端视为在知识库根。
    若传 knowledge_base_id 则只返回该知识库下文档的归属。
    """
    query = select(DocFolderAssignment.document_id, DocFolderAssignment.parent_key)
    if knowledge_base_id is not None:
        subq = select(Document.id).where(Document.knowledge_base_id == knowledge_base_id)
        query = query.where(DocFolderAssignment.document_id.in_(subq))
    result = await db.execute(query)
    out = {}
    for doc_id, parent_key in result.all():
        out[str(doc_id)] = parent_key
    return out


async def set_folder_assignment(db: AsyncSession, document_id: int, parent_key: str):
    """设置单个文档的归属。若 parent_key 为 kb-{id} 则删除记录表示在根下。"""
    await db.execute(delete(DocFolderAssignment).where(DocFolderAssignment.document_id == document_id))
    if not parent_key.startswith("kb-"):
        db.add(DocFolderAssignment(document_id=document_id, parent_key=parent_key))
        await db.flush()


async def set_folder_assignments_batch(db: AsyncSession, assignments: dict):
    """
    assignments: { "docId": "parentKey", ... }，数字 docId 会转成 int。
    若 parent_key 为 kb- 开头则删除该文档的归属记录，否则先删后插。
    """
    for doc_id_str, parent_key in assignments.items():
        try:
            doc_id = int(doc_id_str)
        except (TypeError, ValueError):
            continue
        await db.execute(delete(DocFolderAssignment).where(DocFolderAssignment.document_id == doc_id))
        if not parent_key.startswith("kb-"):
            db.add(DocFolderAssignment(document_id=doc_id, parent_key=parent_key))
    await db.flush()


# ==================== DocumentChunk CRUD ====================

async def create_chunks(db: AsyncSession, document_id: int, chunks: List[dict]) -> List[DocumentChunk]:
    """批量创建文档分块"""
    chunk_objs = [
        DocumentChunk(
            document_id=document_id,
            chunk_index=i,
            content=chunk["content"],
            token_count=chunk.get("token_count", 0),
            embedding_id=chunk.get("embedding_id"),
            extra_data=chunk.get("extra_data"),
        )
        for i, chunk in enumerate(chunks)
    ]
    db.add_all(chunk_objs)
    await db.flush()
    return chunk_objs


async def get_chunks_by_document(db: AsyncSession, document_id: int) -> List[DocumentChunk]:
    """获取文档的所有分块"""
    result = await db.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index)
    )
    return list(result.scalars().all())


# ==================== ChatSession CRUD ====================

async def create_session(
    db: AsyncSession,
    session_key: str,
    title: str = "新对话",
    description: str = None,
    user_id: int = None,
    knowledge_base_id: int = None,
    model_config: dict = None,
    parent_session_key: str = None,
) -> ChatSession:
    """创建会话。parent_session_key 非空时表示对话属于某助手；description 为助手角色描述（app_ 时有效）"""
    session = ChatSession(
        session_key=session_key,
        parent_session_key=parent_session_key,
        title=title,
        description=description,
        user_id=user_id,
        knowledge_base_id=knowledge_base_id,
        model_config=model_config,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_key: str) -> Optional[ChatSession]:
    """获取会话"""
    result = await db.execute(select(ChatSession).where(ChatSession.session_key == session_key))
    return result.scalar_one_or_none()


async def get_session_with_messages(db: AsyncSession, session_key: str, limit: int = 20) -> Optional[ChatSession]:
    """获取会话及其消息"""
    result = await db.execute(
        select(ChatSession).options(selectinload(ChatSession.messages)).where(ChatSession.session_key == session_key)
    )
    session = result.scalar_one_or_none()
    if session and limit:
        session.messages = session.messages[-limit:]
    return session


async def get_user_sessions(
    db: AsyncSession,
    user_id: int,
    knowledge_base_id: int = None,
    limit: int = 50,
) -> List[ChatSession]:
    """获取用户的会话列表"""
    query = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.updated_at.desc())
    if knowledge_base_id:
        query = query.where(ChatSession.knowledge_base_id == knowledge_base_id)
    query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_conversations_by_app(
    db: AsyncSession,
    app_session_key: str,
    user_id: int = None,
    limit: int = 50,
) -> List[ChatSession]:
    """获取某助手下所有对话（conv_ 开头，parent_session_key 为 app）"""
    query = (
        select(ChatSession)
        .where(ChatSession.parent_session_key == app_session_key)
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
    )
    if user_id is not None:
        # 包含当前用户的对话，以及 user_id 为空的对话（兼容历史数据或外部创建的会话）
        query = query.where(or_(ChatSession.user_id == user_id, ChatSession.user_id.is_(None)))
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_conversations_by_app(db: AsyncSession, app_session_key: str, user_id: int = None) -> int:
    """统计某助手下对话数量"""
    query = select(func.count()).select_from(ChatSession).where(ChatSession.parent_session_key == app_session_key)
    if user_id is not None:
        query = query.where(or_(ChatSession.user_id == user_id, ChatSession.user_id.is_(None)))
    result = await db.execute(query)
    return result.scalar() or 0


async def update_session(db: AsyncSession, session_key: str, **kwargs):
    """更新会话"""
    kwargs["updated_at"] = datetime.now()
    await db.execute(update(ChatSession).where(ChatSession.session_key == session_key).values(**kwargs))


async def delete_session(db: AsyncSession, session_key: str):
    """删除会话及其消息。先删消息再删会话，避免依赖 DB 外键 CASCADE。"""
    subq = select(ChatSession.id).where(ChatSession.session_key == session_key)
    await db.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(subq)))
    await db.execute(delete(ChatSession).where(ChatSession.session_key == session_key))


async def delete_conversations_by_app(db: AsyncSession, app_session_key: str):
    """删除某助手下所有对话及其消息（删除助手时级联调用）。先删消息再删会话，避免依赖 DB 外键 CASCADE。"""
    subq = select(ChatSession.id).where(ChatSession.parent_session_key == app_session_key)
    await db.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(subq)))
    await db.execute(delete(ChatSession).where(ChatSession.parent_session_key == app_session_key))


# ==================== ChatMessage CRUD ====================

async def create_message(
    db: AsyncSession,
    session_id: int,
    role: str,
    content: str,
    tokens_used: int = 0,
    model: str = None,
    latency_ms: int = None,
    extra_data: dict = None,
) -> ChatMessage:
    """创建消息"""
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        tokens_used=tokens_used,
        model=model,
        latency_ms=latency_ms,
        extra_data=extra_data,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return msg


async def get_session_messages(db: AsyncSession, session_id: int, limit: int = 50) -> List[ChatMessage]:
    """获取会话消息"""
    result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.desc()).limit(limit)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    return messages


# ==================== QueryLog CRUD ====================

async def create_query_log(
    db: AsyncSession,
    query: str,
    knowledge_base_id: int = None,
    search_app_id: int = None,
    answer: str = None,
    sources: List[dict] = None,
    top_k: int = 3,
    model: str = None,
    tokens_used: int = 0,
    latency_ms: int = 0,
    user_id: str = None,
    ip_address: str = None,
    success: bool = True,
    error_message: str = None,
    title: str = None,
    model_config: dict = None,
) -> QueryLog:
    """创建查询日志"""
    log = QueryLog(
        knowledge_base_id=knowledge_base_id,
        search_app_id=search_app_id,
        query=query,
        answer=answer,
        sources=sources,
        top_k=top_k,
        model=model,
        tokens_used=tokens_used,
        latency_ms=latency_ms,
        user_id=user_id,
        ip_address=ip_address,
        success=success,
        error_message=error_message,
        title=title,
        model_config=model_config,
    )
    db.add(log)
    await db.flush()
    return log


async def get_query_logs(
    db: AsyncSession,
    knowledge_base_id: int = None,
    search_app_id: int = None,
    user_id: str = None,
    success: bool = None,
) -> List[QueryLog]:
    """获取查询日志"""
    query = select(QueryLog).order_by(QueryLog.created_at.desc())
    if knowledge_base_id:
        query = query.where(QueryLog.knowledge_base_id == knowledge_base_id)
    if search_app_id:
        query = query.where(QueryLog.search_app_id == search_app_id)
    if user_id:
        query = query.where(QueryLog.user_id == user_id)
    if success is not None:
        query = query.where(QueryLog.success == success)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_query_logs_by_user(
    db: AsyncSession,
    user_id: str = None,
    limit: int = 100,
) -> List[QueryLog]:
    """获取指定用户的查询日志，按创建时间倒序排列"""
    query = select(QueryLog).order_by(QueryLog.created_at.desc())
    if user_id:
        query = query.where(QueryLog.user_id == user_id)
    else:
        # 如果没有指定用户ID，只返回最近的记录（用于匿名用户或测试）
        query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_query_log_by_id(db: AsyncSession, log_id: int) -> Optional[QueryLog]:
    """根据 id 获取单条查询日志"""
    result = await db.execute(select(QueryLog).where(QueryLog.id == log_id))
    return result.scalar_one_or_none()


async def delete_query_log(db: AsyncSession, log_id: int) -> bool:
    """删除单条查询日志"""
    result = await db.execute(delete(QueryLog).where(QueryLog.id == log_id))
    return result.rowcount > 0


async def clear_query_logs(
    db: AsyncSession,
    knowledge_base_id: Optional[int] = None,
    search_app_id: Optional[int] = None,
    user_id: Optional[str] = None
) -> int:
    """清空查询日志（支持按知识库、检索应用或用户过滤），返回删除的记录数"""
    if knowledge_base_id is None and search_app_id is None and user_id is None:
        raise ValueError("必须至少提供 knowledge_base_id、search_app_id 或 user_id 参数")

    query = delete(QueryLog)
    if knowledge_base_id is not None:
        query = query.where(QueryLog.knowledge_base_id == knowledge_base_id)
    if search_app_id is not None:
        query = query.where(QueryLog.search_app_id == search_app_id)
    if user_id is not None:
        query = query.where(QueryLog.user_id == user_id)

    result = await db.execute(query)
    return result.rowcount


async def clear_query_logs_by_user(
    db: AsyncSession,
    user_id: Optional[str] = None
) -> int:
    """清空指定用户的所有查询日志，返回删除的记录数"""
    query = delete(QueryLog)
    if user_id is not None:
        query = query.where(QueryLog.user_id == user_id)

    result = await db.execute(query)
    return result.rowcount


# ==================== SystemLog CRUD ====================

async def create_system_log(
    db: AsyncSession,
    level: str,
    module: str,
    message: str,
    trace: str = None,
    extra: dict = None,
    request_id: str = None,
    user_id: str = None,
    ip_address: str = None,
) -> SystemLog:
    """创建系统日志"""
    log = SystemLog(
        level=level, module=module, message=message, trace=trace,
        extra=extra, request_id=request_id, user_id=user_id, ip_address=ip_address,
    )
    db.add(log)
    await db.flush()
    return log


async def get_system_logs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    level: str = None,
    module: str = None,
) -> List[SystemLog]:
    """获取系统日志"""
    query = select(SystemLog).order_by(SystemLog.created_at.desc())
    if level:
        query = query.where(SystemLog.level == level)
    if module:
        query = query.where(SystemLog.module == module)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


# ==================== SystemConfig CRUD（ES/解析服务配置）====================

ES_CONFIG_KEYS = (
    "linkrag_server_url",
    "linkrag_es_index",
    "elasticsearch_url",
    "elasticsearch_username",
    "elasticsearch_password",
    "embedding_base_url",
    "embedding_model",
)


async def get_system_config_value(db: AsyncSession, config_key: str) -> Optional[str]:
    """根据 key 获取配置值"""
    result = await db.execute(
        select(SystemConfig.config_value).where(SystemConfig.config_key == config_key)
    )
    return result.scalar_one_or_none()


async def set_system_config(db: AsyncSession, config_key: str, config_value: Optional[str]) -> None:
    """设置配置项（存在则更新，不存在则插入）"""
    result = await db.execute(select(SystemConfig).where(SystemConfig.config_key == config_key))
    existing = result.scalar_one_or_none()
    if existing:
        existing.config_value = config_value
        existing.updated_at = datetime.now()
    else:
        db.add(SystemConfig(config_key=config_key, config_value=config_value))


async def get_es_config(db: AsyncSession) -> dict:
    """
    获取 ES/解析服务相关配置（用于文档解析、trigger-parse 等）。
    仅包含在 DB 中有记录的 key（便于区分「未配置」与「已清空」：已清空时不再回退到 .env）。
    """
    out = {}
    for key in ES_CONFIG_KEYS:
        result = await db.execute(select(SystemConfig).where(SystemConfig.config_key == key))
        row = result.scalar_one_or_none()
        if row is not None:
            out[key] = (row.config_value or "").strip() or None
    return out


# ==================== 语言切换（假实现：存 SystemConfig，前端展示用）====================

UI_LOCALE_KEY = "ui_locale"
VALID_LOCALES = ("zh", "ja", "en")


async def get_ui_locale(db: AsyncSession) -> str:
    """获取当前 UI 语言，默认 zh"""
    val = await get_system_config_value(db, UI_LOCALE_KEY)
    return val if val in VALID_LOCALES else "zh"


async def set_ui_locale(db: AsyncSession, locale: str) -> None:
    """设置 UI 语言（zh/ja/en）"""
    if locale not in VALID_LOCALES:
        raise ValueError(f"invalid locale: {locale}")
    await set_system_config(db, UI_LOCALE_KEY, locale)


# ==================== SearchApp CRUD ====================

async def create_search_app(
    db: AsyncSession,
    name: str,
    description: str = None,
    avatar: str = None,
    kb_ids: List[int] = None,
    similarity_threshold: float = 0.2,
    vector_similarity_weight: float = 0.3,
    rerank_id: str = None,
    use_rerank: bool = False,
    top_k: int = 1024,
    summary: bool = False,
    llm_id: str = None,
    temperature: float = 0.1,
    top_p: float = 0.3,
    presence_penalty: float = 0.4,
    frequency_penalty: float = 0.7,
    related_search: bool = False,
    query_mindmap: bool = False,
    search_method: str = None,
    creator_id: int = None,
) -> SearchApp:
    """创建搜索应用"""
    app = SearchApp(
        name=name,
        description=description,
        avatar=avatar,
        kb_ids=kb_ids,
        similarity_threshold=similarity_threshold,
        vector_similarity_weight=vector_similarity_weight,
        rerank_id=rerank_id,
        use_rerank=use_rerank,
        top_k=top_k,
        summary=summary,
        llm_id=llm_id,
        temperature=temperature,
        top_p=top_p,
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
        related_search=related_search,
        query_mindmap=query_mindmap,
        search_method=search_method,
        creator_id=creator_id,
    )
    db.add(app)
    await db.flush()
    await db.refresh(app)
    return app


async def get_search_apps(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    creator_id: int = None,
) -> List[SearchApp]:
    """获取搜索应用列表"""
    query = select(SearchApp).order_by(SearchApp.created_at.desc())
    if creator_id:
        query = query.where(SearchApp.creator_id == creator_id)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_search_app_by_id(db: AsyncSession, app_id: int) -> Optional[SearchApp]:
    """根据ID获取搜索应用"""
    result = await db.execute(select(SearchApp).where(SearchApp.id == app_id))
    return result.scalar_one_or_none()


async def update_search_app(db: AsyncSession, app_id: int, **kwargs) -> bool:
    """更新搜索应用"""
    kwargs["updated_at"] = datetime.now()
    result = await db.execute(
        update(SearchApp).where(SearchApp.id == app_id).values(**kwargs)
    )
    return result.rowcount > 0


async def delete_search_app(db: AsyncSession, app_id: int) -> bool:
    """删除搜索应用"""
    result = await db.execute(delete(SearchApp).where(SearchApp.id == app_id))
    return result.rowcount > 0
