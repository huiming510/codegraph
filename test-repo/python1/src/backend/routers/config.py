"""配置：当前 LLM/嵌入配置状态、ES 环境配置"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, crud
from config import settings
from .common import success_response
from .llm import get_llm_instance
from .embedding import get_embedding_config

router = APIRouter(prefix="/api/config", tags=["配置"])


@router.get("/current")
async def get_current_config():
    """获取当前配置状态"""
    llm = get_llm_instance()
    embedding_config = get_embedding_config()
    return success_response(
        data={
            "llm_provider": llm.config.provider.value,
            "llm_model": llm.config.model,
            "embedding_provider": embedding_config["provider"],
            "embedding_model": embedding_config["model"],
        }
    )


class EsConfigUpdate(BaseModel):
    """ES/解析服务配置更新"""
    linkrag_server_url: Optional[str] = None
    linkrag_es_index: Optional[str] = None
    elasticsearch_url: Optional[str] = None
    elasticsearch_username: Optional[str] = None
    elasticsearch_password: Optional[str] = None
    embedding_base_url: Optional[str] = None
    embedding_model: Optional[str] = None


def _norm(x: Optional[str]) -> Optional[str]:
    """空字符串视为未配置"""
    return (x or "").strip() or None


def _es_config_response(cfg: dict) -> dict:
    """从 DB 配置与 settings 合并出返回给前端的 ES 配置；DB 中已存在的 key 优先用 DB 值（含清空），否则回退 settings。"""
    return {
        "linkrag_server_url": _norm(cfg["linkrag_server_url"] if "linkrag_server_url" in cfg else settings.linkrag_server_url),
        "linkrag_es_index": _norm(cfg["linkrag_es_index"] if "linkrag_es_index" in cfg else settings.linkrag_es_index) or "linkrag",
        "elasticsearch_url": _norm(cfg["elasticsearch_url"] if "elasticsearch_url" in cfg else settings.elasticsearch_url),
        "elasticsearch_username": _norm(cfg["elasticsearch_username"] if "elasticsearch_username" in cfg else settings.elasticsearch_username),
        "elasticsearch_password": cfg["elasticsearch_password"] if "elasticsearch_password" in cfg else settings.elasticsearch_password,
        "embedding_base_url": _norm(cfg["embedding_base_url"] if "embedding_base_url" in cfg else settings.embedding_base_url),
        "embedding_model": _norm(cfg["embedding_model"] if "embedding_model" in cfg else settings.embedding_model),
    }


@router.get("/es")
async def get_es_config(db: AsyncSession = Depends(get_db)):
    """获取 ES 环境配置（解析服务、ES 地址/用户/密码等）。未配置项为 null，前端/解析逻辑会回退到 .env。"""
    cfg = await crud.get_es_config(db)
    return success_response(data=_es_config_response(cfg))


@router.put("/es")
async def update_es_config(
    body: EsConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新 ES 环境配置并持久化到数据库；每次保存都会写入全部字段（含清空为 null），确保与表单一致。"""
    await crud.set_system_config(db, "linkrag_server_url", (body.linkrag_server_url or "").strip() or None)
    await crud.set_system_config(db, "linkrag_es_index", (body.linkrag_es_index or "").strip() or None)
    await crud.set_system_config(db, "elasticsearch_url", (body.elasticsearch_url or "").strip() or None)
    await crud.set_system_config(db, "elasticsearch_username", (body.elasticsearch_username or "").strip() or None)
    await crud.set_system_config(db, "elasticsearch_password", (body.elasticsearch_password or "").strip() or None)
    await crud.set_system_config(db, "embedding_base_url", (body.embedding_base_url or "").strip() or None)
    await crud.set_system_config(db, "embedding_model", (body.embedding_model or "").strip() or None)
    await db.commit()
    cfg = await crud.get_es_config(db)
    return success_response(data=_es_config_response(cfg), msg="ES 环境配置已保存")


# ==================== 语言切换（假实现：前端展示用）====================

class LocaleUpdate(BaseModel):
    """语言切换请求"""
    locale: str  # zh | ja | en


@router.get("/locale")
async def get_locale(db: AsyncSession = Depends(get_db)):
    """获取当前 UI 语言"""
    locale = await crud.get_ui_locale(db)
    return success_response(data={"locale": locale})


@router.put("/locale")
async def set_locale(body: LocaleUpdate, db: AsyncSession = Depends(get_db)):
    """设置 UI 语言（zh/ja/en）"""
    try:
        await crud.set_ui_locale(db, body.locale)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    return success_response(data={"locale": body.locale}, msg="语言已切换")
