"""知识库：列表、创建、详情、更新、删除、文档列表"""
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db, crud
from logger import logger
from server import LinkragServerClient
from .common import success_response
from .deps import require_user

UPLOAD_DIR = settings.upload_dir


async def _get_linkrag_server_url(db: AsyncSession) -> str | None:
    """解析服务地址：DB 非空优先，否则回退 .env（DB 存空值时也使用 .env）"""
    cfg = await crud.get_es_config(db)
    db_val = cfg.get("linkrag_server_url") if "linkrag_server_url" in cfg else None
    raw = (db_val or "").strip() or (settings.linkrag_server_url or "").strip()
    return raw or None

router = APIRouter(prefix="/api/knowledge-bases", tags=["知识库"])


def _normalize_chunk_strategy(value: str | None) -> str:
    return (value or "general").strip() or "general"


def _validate_chunk_params(chunk_size: int | None, chunk_overlap: int | None):
    if chunk_size is not None and int(chunk_size) <= 0:
        raise HTTPException(status_code=400, detail="chunk_size 必须大于 0")
    if chunk_overlap is not None and int(chunk_overlap) < 0:
        raise HTTPException(status_code=400, detail="chunk_overlap 不能小于 0")
    if chunk_size is not None and chunk_overlap is not None and int(chunk_overlap) >= int(chunk_size):
        raise HTTPException(status_code=400, detail="chunk_overlap 必须小于 chunk_size")


async def _sync_text_pipeline(db: AsyncSession, kb, index_name: str):
    linkrag_url = await _get_linkrag_server_url(db)
    if not linkrag_url:
        logger.warning(
            f"未配置 linkrag_server_url，跳过同步解析参数: kb_id={kb.id}, index={index_name}, "
            f"chunk_size={kb.chunk_size}, chunk_overlap={kb.chunk_overlap}, chunk_strategy={kb.chunk_strategy}"
        )
        return
    try:
        client = LinkragServerClient(base_url=linkrag_url)
        ok = await client.update_text_pipeline_async(
            index=index_name,
            chunk_size=kb.chunk_size,
            chunk_overlap=kb.chunk_overlap,
            chunk_strategy=kb.chunk_strategy,
        )
        if not ok:
            logger.warning(f"同步解析参数未成功: kb_id={kb.id}, index={index_name}")
    except Exception as e:
        logger.warning(f"同步解析参数失败: kb_id={kb.id}, index={index_name}, error={e}")


class KnowledgeBaseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = "📚"
    color: Optional[str] = "#667eea"
    is_public: Optional[bool] = True
    es_id: Optional[str] = None  # 绑定的 ES 索引名，不填则用 linkrag_kb_{id}
    chunk_size: Optional[int] = 4096
    chunk_overlap: Optional[int] = 256
    chunk_strategy: Optional[str] = "general"


class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_public: Optional[bool] = None
    es_id: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    chunk_strategy: Optional[str] = None
    session_id: Optional[str] = None


@router.get("")
async def get_knowledge_bases(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """获取知识库列表（公开接口）"""
    kbs = await crud.get_knowledge_bases(db, skip=skip, limit=limit)
    total = await crud.count_knowledge_bases(db)
    return success_response(
        data={
            "knowledge_bases": [
                {
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description,
                    "icon": kb.icon,
                    "color": kb.color,
                    "document_count": kb.document_count,
                    "is_public": kb.is_public,
                    "es_id": kb.es_id,
                    "chunk_size": kb.chunk_size,
                    "chunk_overlap": kb.chunk_overlap,
                    "chunk_strategy": kb.chunk_strategy,
                    "created_at": kb.created_at.isoformat(),
                }
                for kb in kbs
            ],
            "total": total,
        }
    )


@router.post("")
async def create_knowledge_base(
    request: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_user),
):
    """创建知识库；若配置了解析服务，会同步在 ES 中创建对应索引（es_id 或 linkrag_kb_{id}）"""
    if not request.name.strip():
        raise HTTPException(status_code=400, detail="知识库名称不能为空")
    
    existing_name = await crud.get_knowledge_base_by_name(db, request.name.strip())
    if existing_name:
        raise HTTPException(status_code=400, detail="同名知识库已存在")

    _validate_chunk_params(request.chunk_size, request.chunk_overlap)
    requested_es_id = (request.es_id or "").strip() or None
    if requested_es_id:
        existing = await crud.get_knowledge_base_by_es_id(db, requested_es_id)
        if existing:
            raise HTTPException(status_code=400, detail=f"es_id 已被知识库 {existing.id} 占用")
    kb = await crud.create_knowledge_base(
        db=db,
        name=request.name.strip(),
        description=request.description,
        icon=request.icon,
        color=request.color,
        creator_id=current_user.id,
        is_public=request.is_public,
        es_id=requested_es_id,
        chunk_size=int(request.chunk_size or 4096),
        chunk_overlap=int(request.chunk_overlap or 256),
        chunk_strategy=_normalize_chunk_strategy(request.chunk_strategy),
    )
    await db.commit()
    index_name = LinkragServerClient.resolve_kb_index_name(kb)
    # 统一走解析服务接口创建索引（/index/info + /index/create）
    linkrag_url = await _get_linkrag_server_url(db)
    if linkrag_url:
        try:
            client = LinkragServerClient(base_url=linkrag_url)
            created = await client.create_index_async(index_name)
            if not created:
                logger.warning(f"解析服务侧创建索引未成功: {index_name}")
        except Exception as e:
            logger.warning(f"创建知识库后调用解析服务创建索引失败: kb_id={kb.id}, error={e}")
    else:
        logger.warning(f"未配置 linkrag_server_url，跳过解析服务建索引: kb_id={kb.id}, index={index_name}")
    await _sync_text_pipeline(db, kb, index_name)
    logger.info(f"创建知识库: {kb.name} | 用户: {current_user.username}")
    return success_response(
        data={
            "success": True,
            "knowledge_base": {
                "id": kb.id,
                "name": kb.name,
                "description": kb.description,
                "icon": kb.icon,
                "color": kb.color,
                "es_id": kb.es_id,
                "chunk_size": kb.chunk_size,
                "chunk_overlap": kb.chunk_overlap,
                "chunk_strategy": kb.chunk_strategy,
            },
        }
    )


@router.get("/{kb_id}")
async def get_knowledge_base(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取知识库详情"""
    kb = await crud.get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return success_response(
        data={
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "icon": kb.icon,
            "color": kb.color,
            "document_count": kb.document_count,
            "is_public": kb.is_public,
            "es_id": kb.es_id,
            "chunk_size": kb.chunk_size,
            "chunk_overlap": kb.chunk_overlap,
            "chunk_strategy": kb.chunk_strategy,
            "created_at": kb.created_at.isoformat(),
        }
    )


@router.put("/{kb_id}")
async def update_knowledge_base(
    kb_id: int,
    request: KnowledgeBaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_user),
):
    """更新知识库"""
    kb = await crud.get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    update_data = {k: v for k, v in request.dict().items() if v is not None and k != "session_id"}
    
    if "name" in update_data:
        update_data["name"] = update_data["name"].strip()
        if not update_data["name"]:
            raise HTTPException(status_code=400, detail="知识库名称不能为空")
        existing_name = await crud.get_knowledge_base_by_name(db, update_data["name"])
        if existing_name and existing_name.id != kb_id:
            raise HTTPException(status_code=400, detail="同名知识库已存在")

    _validate_chunk_params(update_data.get("chunk_size"), update_data.get("chunk_overlap"))
    if update_data.get("es_id") is not None:
        update_data["es_id"] = (update_data["es_id"] or "").strip() or None
        if update_data["es_id"]:
            existing = await crud.get_knowledge_base_by_es_id(db, update_data["es_id"])
            if existing and existing.id != kb_id:
                raise HTTPException(status_code=400, detail=f"es_id 已被知识库 {existing.id} 占用")
    if update_data.get("chunk_strategy") is not None:
        update_data["chunk_strategy"] = _normalize_chunk_strategy(update_data.get("chunk_strategy"))
    if update_data:
        await crud.update_knowledge_base(db, kb_id, **update_data)
        await db.commit()
        await db.refresh(kb)
        # 若更新了 es_id，确保新索引在 ES 中存在
        if "es_id" in update_data:
            index_name = LinkragServerClient.resolve_kb_index_name(kb)
            linkrag_url = await _get_linkrag_server_url(db)
            if linkrag_url and index_name:
                try:
                    client = LinkragServerClient(base_url=linkrag_url)
                    created = await client.create_index_async(index_name)
                    if not created:
                        logger.warning(f"更新知识库后解析服务创建索引未成功: kb_id={kb_id}, index={index_name}")
                except Exception as e:
                    logger.warning(f"更新知识库后调用解析服务创建索引失败: kb_id={kb_id}, index={index_name}, error={e}")
        if any(k in update_data for k in ("es_id", "chunk_size", "chunk_overlap", "chunk_strategy")):
            index_name = LinkragServerClient.resolve_kb_index_name(kb)
            await _sync_text_pipeline(db, kb, index_name)

    logger.info(f"更新知识库: {kb.name}")
    return success_response(data={"success": True})


@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_user),
):
    """删除知识库；索引删除统一走解析服务接口（/index/delete）。"""
    kb = await crud.get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    index_name = LinkragServerClient.resolve_kb_index_name(kb)
    linkrag_not_configured = False
    # 通知解析服务删除索引（与创建时 create_index_async 对应）
    linkrag_url = await _get_linkrag_server_url(db)
    if linkrag_url:
        try:
            client = LinkragServerClient(base_url=linkrag_url)
            deleted = await client.delete_index_async(index_name)
            if not deleted:
                logger.warning(f"删除知识库时解析服务删除索引未成功: kb_id={kb_id}, index={index_name}")
        except Exception as e:
            logger.warning(f"删除知识库时调用解析服务删除索引失败: kb_id={kb_id}, error={e}")
    else:
        logger.warning(f"未配置 linkrag_server_url，跳过解析服务删索引: kb_id={kb_id}, index={index_name}")
        linkrag_not_configured = True

    # 删除该知识库下所有文档的磁盘文件（仅上传目录内的文件），再删除表数据
    docs = await crud.get_documents(db, knowledge_base_id=kb_id, limit=100000)
    upload_abs = os.path.abspath(UPLOAD_DIR)
    for doc in docs:
        if doc.file_path and os.path.exists(doc.file_path) and os.path.abspath(doc.file_path).startswith(upload_abs):
            try:
                os.remove(doc.file_path)
            except Exception as e:
                logger.warning(f"删除知识库时移除文档文件失败: {doc.file_path}, error={e}")
    await crud.delete_knowledge_base(db, kb_id)
    await db.commit()
    logger.info(f"删除知识库: {kb.name}")
    return success_response(
        data={"success": True, "linkrag_not_configured": linkrag_not_configured}
    )


@router.get("/{kb_id}/documents")
async def get_kb_documents(
    kb_id: int,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """获取知识库的文档列表"""
    kb = await crud.get_knowledge_base(db, kb_id)
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    docs = await crud.get_documents(db, knowledge_base_id=kb_id, skip=skip, limit=limit)
    return success_response(
        data={
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "upload_time": doc.created_at.isoformat(),
                    "size": doc.file_size,
                    "tags": doc.tags or [],
                    "status": doc.status,
                    "chunk_count": doc.chunk_count or 0,
                }
                for doc in docs
            ]
        }
    )
