from datetime import datetime
from typing import Optional

from flask_login import UserMixin
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, Float, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class ConfigEntry(Base):
    __tablename__ = "config_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class UserConfig(Base):
    """Персональная конфигурация пользователя для работы с S3 (может быть несколько конфигов на пользователя)"""
    __tablename__ = "user_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    
    # Название конфигурации для идентификации
    name: Mapped[str] = mapped_column(String(255), nullable=False, default='Default')
    # Флаг конфигурации по умолчанию (один конфиг по умолчанию на пользователя)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # Пути и подключения
    nfs_path: Mapped[str] = mapped_column(String(512), nullable=False)
    s3_endpoint: Mapped[str] = mapped_column(String(512), nullable=False)
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_access_key: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_secret_key: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Настройки загрузки
    file_age_hours: Mapped[int] = mapped_column(Integer, default=24)
    max_threads: Mapped[int] = mapped_column(Integer, default=5)
    backup_days: Mapped[int] = mapped_column(Integer, default=7)
    storage_class: Mapped[str] = mapped_column(String(50), default='STANDARD')
    enable_tape_storage: Mapped[bool] = mapped_column(Boolean, default=False)
    upload_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_delay: Mapped[int] = mapped_column(Integer, default=5)
    
    # Категории файлов и маппинг расширений (JSON)
    file_categories: Mapped[str] = mapped_column(Text, nullable=True)  # JSON список
    ext_tag_map: Mapped[str] = mapped_column(Text, nullable=True)  # JSON словарь
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        {"sqlite_autoincrement": True} if "sqlite" in str(type(Base)) else {},
    )


class SyncHistoryDB(Base):
    """История синхронизаций в БД"""
    __tablename__ = "sync_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    schedule_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    schedule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    status: Mapped[str] = mapped_column(String(50), nullable=False, default='running', index=True)  # running, completed, failed, cancelled
    
    files_processed: Mapped[int] = mapped_column(Integer, default=0)
    files_uploaded: Mapped[int] = mapped_column(Integer, default=0)
    files_failed: Mapped[int] = mapped_column(Integer, default=0)
    
    total_size: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_size: Mapped[int] = mapped_column(Integer, default=0)
    
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_sync_history_schedule_user', 'schedule_id', 'user_id'),
        Index('idx_sync_history_start_time', 'start_time'),
        {"sqlite_autoincrement": True} if "sqlite" in str(type(Base)) else {},
    )
    
    def to_dict(self) -> dict:
        """Конвертация в словарь"""
        return {
            'id': str(self.id),
            'schedule_id': self.schedule_id,
            'schedule_name': self.schedule_name,
            'user_id': self.user_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'files_processed': self.files_processed,
            'files_uploaded': self.files_uploaded,
            'files_failed': self.files_failed,
            'total_size': self.total_size,
            'uploaded_size': self.uploaded_size,
            'duration': self.duration,
            'error': self.error
        }

