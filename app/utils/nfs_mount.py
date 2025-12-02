"""
Утилиты для проверки и монтирования NFS шары
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def check_nfs_mounted(mount_point: str) -> bool:
    """
    Проверка, смонтирована ли NFS в указанной точке
    
    Args:
        mount_point: Путь к точке монтирования
        
    Returns:
        True если NFS смонтирована и доступна
    """
    try:
        # Проверка, является ли путь точкой монтирования
        result = subprocess.run(
            ['mountpoint', '-q', mount_point],
            capture_output=True,
            timeout=5
        )
        is_mountpoint = result.returncode == 0
        
        # Проверка доступности для чтения
        is_readable = os.path.exists(mount_point) and os.access(mount_point, os.R_OK)
        
        return is_mountpoint and is_readable
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.warning(f"Ошибка при проверке монтирования NFS: {e}")
        return False


def create_mount_point(mount_point: str, permissions: int = 0o755) -> Tuple[bool, str]:
    """
    Создание точки монтирования с указанными правами
    
    Args:
        mount_point: Путь к точке монтирования
        permissions: Права доступа (по умолчанию 0o755)
        
    Returns:
        Tuple (успех, сообщение)
    """
    mount_path = Path(mount_point)
    
    # Если директория уже существует, проверяем права доступа
    if mount_path.exists():
        if mount_path.is_dir():
            return True, f"Directory already exists: {mount_point}"
        else:
            return False, f"Path exists but is not a directory: {mount_point}"
    
    try:
        # Создаем директорию
        mount_path.mkdir(parents=True, exist_ok=True)
        mount_path.chmod(permissions)
        logger.info(f"Created mount point: {mount_point} with permissions {oct(permissions)}")
        return True, f"Directory created successfully: {mount_point}"
    except PermissionError:
        # Если нет прав, пытаемся через sudo
        try:
            import subprocess
            result = subprocess.run(
                ['sudo', 'mkdir', '-p', mount_point],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Устанавливаем права через sudo
                subprocess.run(
                    ['sudo', 'chmod', oct(permissions)[2:], mount_point],
                    timeout=10
                )
                logger.info(f"Created mount point via sudo: {mount_point}")
                return True, f"Directory created successfully via sudo: {mount_point}"
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, f"Failed to create directory: {error_msg}"
        except FileNotFoundError:
            return False, "sudo command not available"
        except Exception as e:
            return False, f"Error creating directory: {e}"
    except Exception as e:
        return False, f"Failed to create mount point: {e}"


def mount_nfs(nfs_server: str, mount_point: str, nfs_options: Optional[str] = None) -> Tuple[bool, str]:
    """
    Попытка монтирования NFS шары
    
    Args:
        nfs_server: Адрес NFS сервера и путь (например, "172.20.129.1:/backups")
        mount_point: Локальная точка монтирования
        nfs_options: Опции монтирования (по умолчанию: "vers=4.1,soft,timeo=30,retrans=3")
        
    Returns:
        Tuple (успех, сообщение)
    """
    if not nfs_options:
        nfs_options = "vers=4.1,soft,timeo=30,retrans=3,noatime"
    
    # Создание точки монтирования, если не существует
    if not Path(mount_point).exists():
        success, message = create_mount_point(mount_point)
        if not success:
            return False, message
    
    # Проверка, не смонтирована ли уже
    if check_nfs_mounted(mount_point):
        logger.info(f"NFS уже смонтирована в {mount_point}")
        return True, "NFS уже смонтирована"
    
    # Попытка монтирования
    try:
        # Используем mount.nfs напрямую (может потребоваться sudo)
        cmd = ['mount', '-t', 'nfs', '-o', nfs_options, nfs_server, mount_point]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info(f"✅ NFS успешно смонтирована: {nfs_server} -> {mount_point}")
            return True, "NFS успешно смонтирована"
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            logger.error(f"❌ Ошибка монтирования NFS: {error_msg}")
            return False, f"Ошибка монтирования: {error_msg}"
            
    except subprocess.TimeoutExpired:
        return False, "Таймаут при монтировании NFS"
    except Exception as e:
        return False, f"Исключение при монтировании: {e}"


def ensure_nfs_mounted(
    nfs_server: str,
    mount_point: str,
    nfs_options: Optional[str] = None,
    auto_mount: bool = False
) -> Tuple[bool, str]:
    """
    Проверка и при необходимости монтирование NFS
    
    Args:
        nfs_server: Адрес NFS сервера и путь
        mount_point: Локальная точка монтирования
        nfs_options: Опции монтирования
        auto_mount: Попытаться автоматически смонтировать, если не смонтирована
        
    Returns:
        Tuple (доступна ли NFS, сообщение)
    """
    # Проверка текущего состояния
    if check_nfs_mounted(mount_point):
        return True, "NFS доступна"
    
    logger.warning(f"NFS не смонтирована в {mount_point}")
    
    if not auto_mount:
        return False, f"NFS не смонтирована. Используйте скрипт монтирования или настройте automount."
    
    # Попытка автоматического монтирования
    logger.info(f"Попытка автоматического монтирования NFS...")
    success, message = mount_nfs(nfs_server, mount_point, nfs_options)
    
    if success and check_nfs_mounted(mount_point):
        return True, message
    else:
        return False, f"Не удалось смонтировать NFS: {message}"

