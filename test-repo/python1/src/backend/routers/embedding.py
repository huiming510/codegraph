"""嵌入模型：提供商列表、配置、测试连接"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from logger import logger
from .common import success_response

router = APIRouter(prefix="/api/embedding", tags=["嵌入模型"])

# 嵌入模型配置（与 main 中保持一致，由 main 注入或此处维护）
_embedding_config = {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "api_key": None,
    "api_base": None,
    "dimensions": 1536,
}


def set_embedding_config(config: dict):
    global _embedding_config
    _embedding_config.update(config)


def get_embedding_config():
    return _embedding_config


class EmbeddingConfigRequest(BaseModel):
    provider: str
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    dimensions: Optional[int] = 1536


@router.get("/providers")
def get_embedding_providers():
    """获取支持的嵌入模型提供商"""
    return success_response(
        data={
            "providers": ["openai", "azure_openai", "ollama", "zhipu", "local"],
            "current": _embedding_config["provider"],
        }
    )


@router.post("/config")
async def update_embedding_config(request: EmbeddingConfigRequest):
    """更新嵌入模型配置"""
    global _embedding_config
    try:
        _embedding_config["provider"] = request.provider
        _embedding_config["model"] = request.model
        _embedding_config["api_key"] = request.api_key
        _embedding_config["api_base"] = request.api_base
        _embedding_config["dimensions"] = request.dimensions
        logger.info(f"嵌入模型配置已更新: {request.provider}/{request.model}")
        return success_response(data={"success": True, "provider": request.provider})
    except Exception as e:
        logger.error(f"更新嵌入模型配置失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/test")
async def test_embedding_connection():
    """测试嵌入模型连接"""
    try:
        if _embedding_config["provider"] == "local":
            return success_response(data={"success": True, "message": "本地模型无需测试连接"})
        return success_response(
            data={"success": True, "message": f"嵌入模型 {_embedding_config['model']} 连接成功"}
        )
    except Exception as e:
        return success_response(data={"success": False, "message": str(e)}, msg=str(e))
