import datetime

from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models.user import User


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if user is None:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_default_admin_if_needed(db: Session) -> None:
    existing = db.query(User).first()
    if existing is not None:
        return

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    admin = User(
        username="admin",
        password_hash=get_password_hash("admin123"),
        real_name="系统管理员",
        role="admin",
        is_active=1,
        created_at=now,
        updated_at=now,
    )
    db.add(admin)
    db.commit()
