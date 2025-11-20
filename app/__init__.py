"""
S3 Backup Manager - Automatic Veeam backups replication to Quantum ActiveScale via S3 protocol
"""

__version__ = '1.0.0'

from app.services.scheduler_service import scheduler_service

__all__ = ['scheduler_service']