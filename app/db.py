import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""
    pass


def _build_connection_url() -> str:
    # Если явно указан DATABASE_URL - используем его
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    # Если явно указано USE_POSTGRES=true - используем PostgreSQL
    use_postgres = os.getenv("USE_POSTGRES", "false").lower() == "true"
    
    if use_postgres:
        user = os.getenv("POSTGRES_USER", "backup_admin")
        password = os.getenv("POSTGRES_PASSWORD", "backup_password")
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "backup_manager")
        return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"

    # По умолчанию используем SQLite (для простоты локальной разработки)
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{data_dir / 'app.db'}"


DATABASE_URL = _build_connection_url()


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False))


def init_db() -> None:
    """Create database tables if they do not exist."""
    from app.models import db_models  # noqa: F401  (ensure models are registered)

    Base.metadata.create_all(bind=engine)
    
    # Создание дефолтного администратора, если пользователей нет
    _create_default_admin()


def _create_default_admin() -> None:
    """Create default admin user if no users exist."""
    from app.auth.utils import users_exist, get_user_by_username, create_user
    
    if users_exist():
        return  # Пользователи уже существуют
    
    # Получаем креденшалы из переменных окружения или используем дефолтные
    default_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    default_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
    default_email = os.getenv("DEFAULT_ADMIN_EMAIL", None)
    
    # Проверяем, не существует ли уже такой пользователь
    if get_user_by_username(default_username):
        return
    
    try:
        create_user(
            username=default_username,
            password=default_password,
            email=default_email,
            is_admin=True
        )
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Created default admin user: {default_username}")
        logger.warning(f"⚠️  DEFAULT ADMIN PASSWORD: {default_password} - CHANGE IT AFTER FIRST LOGIN!")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to create default admin user: {e}")


@contextmanager
def session_scope() -> Generator:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

