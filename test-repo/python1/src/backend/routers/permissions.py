"""权限管理：权限列表、检查（管理员）"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, crud
from .common import success_response
from .deps import require_admin

router = APIRouter(prefix="/api/permissions", tags=["权限管理"])


@router.get("")
async def get_permissions(
    role: Optional[str] = Query(None, description="按角色筛选"),
    skip: int = 0,
    limit: int = 200,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取权限列表（管理员）"""
    perms = await crud.get_permissions(db, role=role, skip=skip, limit=limit)
    return success_response(
        data={
            "permissions": [
                {
                    "id": p.id,
                    "role": p.role,
                    "resource": p.resource,
                    "action": p.action,
                    "created_at": p.created_at.isoformat(),
                }
                for p in perms
            ]
        }
    )
