"""登录与认证：登录、注册、当前用户、修改密码"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, crud
from logger import logger
from .common import success_response
from .deps import create_token, require_user

router = APIRouter(prefix="/api/auth", tags=["认证/登录"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    nickname: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    user = await crud.authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    await crud.update_user_last_login(db, user.id)
    await db.commit()

    token = create_token(user.id, user.username, user.role)
    logger.info(f"用户登录成功: {user.username}")

    return success_response(
        data={
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
            },
        }
    )


@router.post("/register")
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """用户注册"""
    existing = await crud.get_user_by_username(db, request.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = await crud.create_user(
        db=db,
        username=request.username,
        password=request.password,
        email=request.email,
        nickname=request.nickname,
    )
    await db.commit()

    token = create_token(user.id, user.username, user.role)
    logger.info(f"用户注册成功: {user.username}")

    return success_response(
        data={
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
            },
        }
    )


@router.post("/logout")
async def logout(user=Depends(require_user)):
    """退出登录（客户端清除 token 即可，服务端仅记录）"""
    logger.info(f"用户退出登录: {user.username}")
    return success_response(data={}, msg="已退出登录")


@router.get("/userinfo")
async def get_me(user=Depends(require_user)):
    """获取当前用户信息"""
    return success_response(
        data={
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
        }
    )


@router.put("/password")
async def change_password(
    request: ChangePasswordRequest,
    user=Depends(require_user),
    db: AsyncSession = Depends(get_db),
):
    """修改密码"""
    if not crud.verify_password(request.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    await crud.update_user_password(db, user.id, request.new_password)
    await db.commit()
    logger.info(f"用户修改密码: {user.username}")

    return success_response(data={"success": True}, msg="密码修改成功")


@router.get("/menu")
async def get_menu(user=Depends(require_user)):
    """获取当前用户可访问的菜单：管理员全部，开发人员(base)全部，用户仅首页/智能问答/智能检索"""
    menu_list = crud.get_menus_for_role(user.role)
    return success_response(data=menu_list)
