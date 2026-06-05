"""用户管理：用户列表、创建、更新、删除（管理员）"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, crud
from logger import logger
from .common import success_response
from .deps import require_admin

router = APIRouter(prefix="/api/users", tags=["用户管理"])

# 允许的角色值：管理员、开发人员(user)、用户(guest)
VALID_ROLES = ("admin", "user", "guest")


class CreateUserRequest(BaseModel):
    """创建用户请求（管理员创建时可选角色）"""
    username: str
    password: str
    email: Optional[str] = None
    nickname: Optional[str] = None
    role: Optional[str] = "user"


class UpdateUserRequest(BaseModel):
    nickname: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    """管理员重置用户密码请求"""
    password: str


@router.get("")
async def get_users(
    skip: int = 0,
    limit: int = 50,
    role: Optional[str] = None,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表（管理员）"""
    users = await crud.get_users(db, skip=skip, limit=limit, role=role)
    total = await crud.count_users(db, role=role)

    return success_response(
        data={
            "users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "nickname": u.nickname,
                    "email": u.email,
                    "role": u.role,
                    "is_active": u.is_active,
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                    "created_at": u.created_at.isoformat(),
                }
                for u in users
            ],
            "total": total,
        }
    )


@router.post("")
async def create_user(
    request: CreateUserRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建用户（管理员），可指定角色：admin/管理员、user/开发人员、guest/用户"""
    existing = await crud.get_user_by_username(db, request.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    role = (request.role or "user").strip().lower()
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail="角色必须是 admin、user 或 guest")

    user = await crud.create_user(
        db=db,
        username=request.username,
        password=request.password,
        email=request.email,
        nickname=request.nickname,
        role=role,
    )
    await db.commit()
    logger.info(f"管理员创建用户: {user.username} 角色: {role}")

    return success_response(data={"success": True, "user_id": user.id})


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """更新用户（管理员）"""
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    update_data = {}
    if request.nickname is not None:
        update_data["nickname"] = request.nickname
    if request.email is not None:
        update_data["email"] = request.email
    if request.role is not None:
        if request.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail="角色必须是 admin、user 或 guest")
        update_data["role"] = request.role
    if request.is_active is not None:
        update_data["is_active"] = request.is_active

    if update_data:
        await crud.update_user(db, user_id, **update_data)
        await db.commit()

    logger.info(f"管理员更新用户: {user.username}")
    return success_response(data={"success": True})


@router.put("/{user_id}/password")
async def reset_user_password(
    user_id: int,
    request: ResetPasswordRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员重置用户密码（用于将用户密码重置为指定值，如 123456）"""
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    await crud.update_user_password(db, user_id, request.password)
    await db.commit()
    logger.info(f"管理员重置用户密码: {user.username}")
    return success_response(data={"success": True})


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除用户（管理员）"""
    user = await crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.role == "admin":
        raise HTTPException(status_code=400, detail="不能删除管理员账户")

    await crud.delete_user(db, user_id)
    await db.commit()
    logger.info(f"管理员删除用户: {user.username}")

    return success_response(data={"success": True})
