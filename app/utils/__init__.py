"""
Utility functions and classes for S3 Backup Manager
"""

from app.utils.config import (
    get_config, update_config, validate_environment, upload_stats,
    get_nfs_path, get_s3_endpoint, get_s3_bucket, get_aws_access_key_id,
    get_aws_secret_access_key, get_max_threads, get_backup_days, get_ext_tag_map,
    get_storage_class, get_enable_tape_storage, get_upload_retries, get_retry_delay
)
from app.utils.schedule_storage import ScheduleStorage
from app.utils.debug_logger import DebugLogger
from app.utils.file_utils import (
    normalize_s3_key, get_file_modification_time, is_file_in_time_range, get_file_info
)
from app.utils.logger import setup_logging
from app.utils.stats_monitor import start_stats_monitor, stop_stats_monitor, print_final_statistics, get_detailed_stats

__all__ = [
    # Config
    'get_config',
    'update_config', 
    'validate_environment',
    'upload_stats',
    'get_nfs_path',
    'get_s3_endpoint',
    'get_s3_bucket',
    'get_aws_access_key_id',
    'get_aws_secret_access_key',
    'get_max_threads',
    'get_backup_days',
    'get_ext_tag_map',
    'get_storage_class',
    'get_enable_tape_storage',
    'get_upload_retries',
    'get_retry_delay',
    
    # Storage
    'ScheduleStorage',
    
    # Logging
    'DebugLogger',
    'setup_logging',
    
    # File utilities
    'normalize_s3_key',
    'get_file_modification_time',
    'is_file_in_time_range',
    'get_file_info',

    # Statistics
    'start_stats_monitor',
    'stop_stats_monitor', 
    'print_final_statistics',
    'get_detailed_stats'
]