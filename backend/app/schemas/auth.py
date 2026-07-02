from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenUser(BaseModel):
    id: int
    username: str
    real_name: str
    role: str


class LoginResponseData(BaseModel):
    access_token: str
    token_type: str
    user: TokenUser


class CurrentUserResponseData(BaseModel):
    id: int
    username: str
    real_name: str
    role: str
    phone: str | None = None
    email: str | None = None
