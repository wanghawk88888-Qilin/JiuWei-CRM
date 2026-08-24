import datetime

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, data: dict) -> User:
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    user = User(
        username=data["username"],
        password_hash=get_password_hash("123456"),
        real_name=data["real_name"],
        role=data["role"],
        phone=data.get("phone"),
        email=data.get("email"),
        is_active=1,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, data: dict) -> User:
    for field, value in data.items():
        if value is not None:
            setattr(user, field, value)
    user.updated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    db.refresh(user)
    return user


def reset_password(db: Session, user: User) -> User:
    user.password_hash = get_password_hash("123456")
    user.updated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, old_password: str, new_password: str) -> bool:
    if not verify_password(old_password, user.password_hash):
        return False
    user.password_hash = get_password_hash(new_password)
    user.updated_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    db.refresh(user)
    return True
