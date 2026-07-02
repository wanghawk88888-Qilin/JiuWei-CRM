from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    CurrentUserResponseData,
    LoginRequest,
    LoginResponseData,
    TokenUser,
)
from app.services.auth_service import authenticate_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.username, request.password)
    if user is None:
        return {
            "success": False,
            "error_code": "UNAUTHORIZED",
            "message": "用户名或密码错误",
        }

    token_data = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role,
    }
    access_token = create_access_token(token_data)

    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "real_name": user.real_name,
                "role": user.role,
            },
        },
        "message": "登录成功",
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "username": current_user.username,
            "real_name": current_user.real_name,
            "role": current_user.role,
            "phone": current_user.phone,
            "email": current_user.email,
        },
        "message": "ok",
    }
