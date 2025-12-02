from typing import Optional

from werkzeug.security import check_password_hash, generate_password_hash

from app.db import session_scope
from app.models.db_models import User


def get_user_by_username(username: str) -> Optional[User]:
    with session_scope() as session:
        return session.query(User).filter(User.username == username).first()


def create_user(username: str, password: str, email: Optional[str] = None, is_admin: bool = False) -> User:
    password_hash = generate_password_hash(password)
    with session_scope() as session:
        user = User(username=username, email=email, password_hash=password_hash, is_admin=is_admin, is_active=True)
        session.add(user)
        session.flush()
        session.refresh(user)
        return user


def verify_password(password_hash: str, password: str) -> bool:
    return check_password_hash(password_hash, password)


def users_exist() -> bool:
    with session_scope() as session:
        return session.query(User).count() > 0





