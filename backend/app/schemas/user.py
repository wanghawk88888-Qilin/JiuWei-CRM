from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    real_name: str
    role: str  # admin, manager, counselor
    phone: str | None = None
    email: str | None = None


class UserUpdate(BaseModel):
    real_name: str | None = None
    role: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: int | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    real_name: str
    role: str
    phone: str | None = None
    email: str | None = None
    is_active: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str
