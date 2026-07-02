from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_admin
from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    ChangePasswordRequest,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services import user_service

router = APIRouter(prefix="/api/v1", tags=["users"])


# -- Helper: format user response -----------------------------------------


def _user_to_response(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "real_name": user.real_name,
        "role": user.role,
        "phone": user.phone,
        "email": user.email,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


# -- User list (admin only) ------------------------------------------------


@router.get("/users")
def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = user_service.list_users(db)
    return {
        "success": True,
        "data": [_user_to_response(u) for u in users],
        "message": "ok",
    }


# -- Create user (admin only) ----------------------------------------------


@router.post("/users")
def create_user(
    request: UserCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # Check duplicate username
    existing = user_service.get_user_by_username(db, request.username)
    if existing:
        return {
            "success": False,
            "error_code": "DUPLICATE_USERNAME",
            "message": "用户名已存在",
        }

    user = user_service.create_user(db, request.model_dump())
    return {
        "success": True,
        "data": _user_to_response(user),
        "message": "用户创建成功，默认密码: 123456，建议首次登录修改密码",
    }


# -- Update user (admin only) ----------------------------------------------


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    request: UserUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        return {
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "用户不存在",
        }

    user = user_service.update_user(db, user, request.model_dump(exclude_unset=True))
    return {
        "success": True,
        "data": _user_to_response(user),
        "message": "用户更新成功",
    }


# -- Reset password (admin only) -------------------------------------------


@router.put("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        return {
            "success": False,
            "error_code": "NOT_FOUND",
            "message": "用户不存在",
        }

    user_service.reset_password(db, user)
    return {
        "success": True,
        "data": None,
        "message": "密码已重置为 123456",
    }


# -- Change own password (any authenticated user) ---------------------------


@router.put("/auth/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if request.new_password != request.confirm_password:
        return {
            "success": False,
            "error_code": "PASSWORD_MISMATCH",
            "message": "两次输入的新密码不一致",
        }

    if len(request.new_password) < 6:
        return {
            "success": False,
            "error_code": "PASSWORD_TOO_SHORT",
            "message": "密码长度不能少于6位",
        }

    success = user_service.change_password(
        db, current_user, request.old_password, request.new_password
    )
    if not success:
        return {
            "success": False,
            "error_code": "WRONG_PASSWORD",
            "message": "旧密码错误",
        }

    return {
        "success": True,
        "data": None,
        "message": "密码修改成功",
    }
