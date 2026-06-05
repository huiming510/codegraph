"""日志：查询日志、系统日志（管理员）"""
from fastapi import APIRouter, Depends
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, crud
from .common import success_response
from .deps import require_admin

router = APIRouter(prefix="/api/logs", tags=["日志"])


@router.get("/query")
async def get_query_logs_api(
    skip: int = 0,
    limit: int = 50,
    success: Optional[bool] = None,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取查询日志（管理员）"""
    logs = await crud.get_query_logs(db, success=success)
    # 手动分页
    logs = logs[skip:skip + limit]
    return success_response(
        data={
            "logs": [
                {
                    "id": log.id,
                    "query": log.query,
                    "answer": log.answer[:100] + "..." if log.answer and len(log.answer) > 100 else log.answer,
                    "latency_ms": log.latency_ms,
                    "success": log.success,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ]
        }
    )


@router.get("/system")
async def get_system_logs_api(
    skip: int = 0,
    limit: int = 50,
    level: Optional[str] = None,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取系统日志（管理员）"""
    logs = await crud.get_system_logs(db, skip=skip, limit=limit, level=level)
    return success_response(
        data={
            "logs": [
                {
                    "id": log.id,
                    "level": log.level,
                    "module": log.module,
                    "message": log.message,
                    "created_at": log.created_at.isoformat(),
                }
                for log in logs
            ]
        }
    )
