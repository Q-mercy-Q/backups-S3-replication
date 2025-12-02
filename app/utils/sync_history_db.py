"""
Утилиты для работы с историей синхронизаций в БД
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import desc

from app.db import session_scope
from app.models.db_models import SyncHistoryDB
from app.models.sync_history import SyncHistory, SyncStatus

logger = logging.getLogger(__name__)


def create_sync_history(
    schedule_id: str,
    schedule_name: str,
    user_id: Optional[int] = None,
    status: str = 'running'
) -> int:
    """Создание новой записи истории синхронизации
    
    Returns:
        ID созданной записи истории
    """
    with session_scope() as session:
        history_entry = SyncHistoryDB(
            schedule_id=schedule_id,
            schedule_name=schedule_name,
            user_id=user_id,
            start_time=datetime.utcnow(),
            status=status,
            files_processed=0,
            files_uploaded=0,
            files_failed=0,
            total_size=0,
            uploaded_size=0,
            duration=0.0
        )
        session.add(history_entry)
        session.flush()
        session.refresh(history_entry)
        history_id = history_entry.id
        # Делаем объект отсоединенным от сессии, чтобы можно было использовать после выхода из контекста
        session.expunge(history_entry)
        return history_id


def update_sync_history(
    history_id: int,
    status: Optional[str] = None,
    files_uploaded: Optional[int] = None,
    files_failed: Optional[int] = None,
    total_size: Optional[int] = None,
    uploaded_size: Optional[int] = None,
    duration: Optional[float] = None,
    error: Optional[str] = None
) -> Optional[SyncHistoryDB]:
    """Обновление записи истории синхронизации"""
    with session_scope() as session:
        history_entry = session.query(SyncHistoryDB).filter(SyncHistoryDB.id == history_id).first()
        if not history_entry:
            logger.error(f"Sync history entry {history_id} not found")
            return None
        
        if status is not None:
            history_entry.status = status
        if files_uploaded is not None:
            history_entry.files_uploaded = files_uploaded
        if files_failed is not None:
            history_entry.files_failed = files_failed
        if total_size is not None:
            history_entry.total_size = total_size
        if uploaded_size is not None:
            history_entry.uploaded_size = uploaded_size
        if duration is not None:
            history_entry.duration = duration
        if error is not None:
            history_entry.error = error
        
        if status in ['completed', 'failed', 'cancelled']:
            history_entry.end_time = datetime.utcnow()
            history_entry.files_processed = (files_uploaded or 0) + (files_failed or 0)
        
        session.flush()
        return history_entry


def get_sync_history(
    schedule_id: Optional[str] = None,
    user_id: Optional[int] = None,
    limit: int = 50,
    period: str = 'all'
) -> List[SyncHistoryDB]:
    """Получение истории синхронизаций с фильтрами"""
    with session_scope() as session:
        query = session.query(SyncHistoryDB)
        
        if schedule_id:
            query = query.filter(SyncHistoryDB.schedule_id == schedule_id)
        if user_id:
            query = query.filter(SyncHistoryDB.user_id == user_id)
        
        # Фильтр по периоду времени
        if period != 'all':
            now = datetime.utcnow()
            if period == 'today':
                start_date = datetime(now.year, now.month, now.day)
                query = query.filter(SyncHistoryDB.start_time >= start_date)
            elif period == 'week':
                from datetime import timedelta
                start_date = now - timedelta(days=now.weekday())
                start_date = datetime(start_date.year, start_date.month, start_date.day)
                query = query.filter(SyncHistoryDB.start_time >= start_date)
            elif period == 'month':
                start_date = datetime(now.year, now.month, 1)
                query = query.filter(SyncHistoryDB.start_time >= start_date)
        
        # Сортируем по времени и ограничиваем количество
        query = query.order_by(desc(SyncHistoryDB.start_time))
        return query.limit(limit).all()


def convert_db_to_dataclass(db_entry: SyncHistoryDB) -> SyncHistory:
    """Конвертация записи БД в dataclass SyncHistory"""
    return SyncHistory(
        id=str(db_entry.id),
        schedule_id=db_entry.schedule_id,
        schedule_name=db_entry.schedule_name,
        start_time=db_entry.start_time.isoformat() if db_entry.start_time else datetime.utcnow().isoformat(),
        status=SyncStatus(db_entry.status),
        files_processed=db_entry.files_processed,
        files_uploaded=db_entry.files_uploaded,
        files_failed=db_entry.files_failed,
        total_size=db_entry.total_size,
        uploaded_size=db_entry.uploaded_size,
        duration=db_entry.duration,
        error=db_entry.error,
        end_time=db_entry.end_time.isoformat() if db_entry.end_time else None
    )


def convert_dataclass_to_db_dict(history: SyncHistory, user_id: Optional[int] = None) -> Dict[str, Any]:
    """Конвертация dataclass SyncHistory в словарь для БД"""
    start_time_str = history.start_time.replace('Z', '+00:00') if 'Z' in history.start_time else history.start_time
    end_time_str = history.end_time.replace('Z', '+00:00') if history.end_time and 'Z' in history.end_time else history.end_time
    
    return {
        'schedule_id': history.schedule_id,
        'schedule_name': history.schedule_name,
        'user_id': user_id,
        'start_time': datetime.fromisoformat(start_time_str) if start_time_str else datetime.utcnow(),
        'end_time': datetime.fromisoformat(end_time_str) if end_time_str else None,
        'status': history.status.value,
        'files_processed': history.files_processed,
        'files_uploaded': history.files_uploaded,
        'files_failed': history.files_failed,
        'total_size': history.total_size,
        'uploaded_size': history.uploaded_size,
        'duration': history.duration,
        'error': history.error
    }

