"""
API маршруты для управления NFS монтированием
"""

import os
import re
import subprocess
import logging
from flask import Flask, jsonify, request
from flask_login import login_required, current_user

from app.utils.nfs_mount import check_nfs_mounted, mount_nfs, create_mount_point
from app.utils.config import get_nfs_path

logger = logging.getLogger(__name__)


def init_routes(app: Flask) -> None:
    """Инициализация маршрутов управления NFS"""
    
    @app.route('/api/nfs/status', methods=['GET'])
    @login_required
    def nfs_status():
        """Проверка статуса монтирования NFS"""
        try:
            mount_point = request.args.get('mount_point') or get_nfs_path()
            
            if not mount_point:
                return jsonify({
                    'status': 'error',
                    'message': 'Mount point not specified'
                }), 400
            
            is_mounted = check_nfs_mounted(mount_point)
            
            # Получаем дополнительную информацию о монтировании
            mount_info = None
            if is_mounted:
                try:
                    result = subprocess.run(
                        ['mount', '-t', 'nfs'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if mount_point in line:
                                mount_info = line.strip()
                                break
                except Exception:
                    pass
            
            return jsonify({
                'status': 'success',
                'mounted': is_mounted,
                'mount_point': mount_point,
                'mount_info': mount_info
            }), 200
            
        except Exception as e:
            logger.error(f"Error checking NFS status: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Error checking NFS status: {str(e)}'
            }), 500
    
    @app.route('/api/nfs/mount', methods=['POST'])
    @login_required
    def nfs_mount():
        """Монтирование NFS шары"""
        try:
            data = request.get_json() or {}
            
            nfs_server = (data.get('nfs_server') or '').strip()
            mount_point = (data.get('mount_point') or '').strip()
            nfs_options = (data.get('nfs_options') or '').strip() or None
            
            # Валидация входных данных
            if not nfs_server:
                return jsonify({
                    'status': 'error',
                    'message': 'NFS server is required (format: SERVER:/path)'
                }), 400
            
            if not mount_point:
                return jsonify({
                    'status': 'error',
                    'message': 'Mount point is required'
                }), 400
            
            # Валидация формата NFS сервера
            if not re.match(r'^[\w\.\-]+:/', nfs_server):
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid NFS server format. Expected: SERVER:/path'
                }), 400
            
            # Валидация пути монтирования (безопасность)
            if not re.match(r'^[\w\.\-/]+$', mount_point) or '..' in mount_point:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid mount point path'
                }), 400
            
            # Ограничение на точки монтирования (только /mnt/* для безопасности)
            if not mount_point.startswith('/mnt/'):
                return jsonify({
                    'status': 'error',
                    'message': 'Mount point must be under /mnt/ directory for security'
                }), 400
            
            logger.info(f"User {current_user.username} attempting to mount NFS: {nfs_server} -> {mount_point}")
            
            # Сначала создаем директорию, если не существует
            from pathlib import Path
            if not Path(mount_point).exists():
                logger.info(f"Creating mount point directory: {mount_point}")
                create_success, create_message = _create_directory_with_sudo(mount_point)
                if not create_success:
                    return jsonify({
                        'status': 'error',
                        'message': f'Failed to create directory: {create_message}'
                    }), 500
            
            # Попытка монтирования
            # Используем sudo для монтирования, если доступен
            success, message = _mount_nfs_with_sudo(nfs_server, mount_point, nfs_options)
            
            if success:
                # Проверяем, действительно ли смонтирована
                if check_nfs_mounted(mount_point):
                    return jsonify({
                        'status': 'success',
                        'message': message,
                        'mount_point': mount_point,
                        'nfs_server': nfs_server
                    }), 200
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Mount command succeeded but NFS is not accessible'
                    }), 500
            else:
                return jsonify({
                    'status': 'error',
                    'message': message
                }), 500
                
        except Exception as e:
            logger.error(f"Error mounting NFS: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Error mounting NFS: {str(e)}'
            }), 500
    
    @app.route('/api/nfs/unmount', methods=['POST'])
    @login_required
    def nfs_unmount():
        """Размонтирование NFS шары"""
        try:
            data = request.get_json() or {}
            mount_point = (data.get('mount_point') or '').strip() or get_nfs_path()
            
            if not mount_point:
                return jsonify({
                    'status': 'error',
                    'message': 'Mount point not specified'
                }), 400
            
            # Валидация пути
            if not mount_point.startswith('/mnt/'):
                return jsonify({
                    'status': 'error',
                    'message': 'Mount point must be under /mnt/ directory'
                }), 400
            
            logger.info(f"User {current_user.username} attempting to unmount NFS: {mount_point}")
            
            # Попытка размонтирования
            success, message = _unmount_nfs_with_sudo(mount_point)
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': message,
                    'mount_point': mount_point
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': message
                }), 500
                
        except Exception as e:
            logger.error(f"Error unmounting NFS: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Error unmounting NFS: {str(e)}'
            }), 500
    
    @app.route('/api/nfs/create-directory', methods=['POST'])
    @login_required
    def nfs_create_directory():
        """Создание локальной директории для монтирования"""
        try:
            data = request.get_json() or {}
            mount_point = (data.get('mount_point') or '').strip()
            permissions = data.get('permissions', '755')
            
            if not mount_point:
                return jsonify({
                    'status': 'error',
                    'message': 'Mount point is required'
                }), 400
            
            # Валидация пути
            if not re.match(r'^[\w\.\-/]+$', mount_point) or '..' in mount_point:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid mount point path'
                }), 400
            
            # Ограничение на точки монтирования (только /mnt/* для безопасности)
            if not mount_point.startswith('/mnt/'):
                return jsonify({
                    'status': 'error',
                    'message': 'Mount point must be under /mnt/ directory for security'
                }), 400
            
            # Преобразование прав доступа
            try:
                perms = int(permissions, 8) if isinstance(permissions, str) else permissions
            except (ValueError, TypeError):
                perms = 0o755
            
            logger.info(f"User {current_user.username} attempting to create directory: {mount_point}")
            
            # Создание директории
            success, message = _create_directory_with_sudo(mount_point, perms)
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': message,
                    'mount_point': mount_point
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': message
                }), 500
                
        except Exception as e:
            logger.error(f"Error creating directory: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Error creating directory: {str(e)}'
            }), 500
    
    @app.route('/api/nfs/test', methods=['POST'])
    @login_required
    def nfs_test():
        """Тестирование доступности NFS сервера"""
        try:
            data = request.get_json() or {}
            nfs_server = (data.get('nfs_server') or '').strip()
            
            if not nfs_server:
                return jsonify({
                    'status': 'error',
                    'message': 'NFS server is required'
                }), 400
            
            # Извлекаем IP/имя сервера
            server_match = re.match(r'^([\w\.\-]+):/', nfs_server)
            if not server_match:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid NFS server format'
                }), 400
            
            server_ip = server_match.group(1)
            
            # Проверка доступности сервера
            try:
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', '2', server_ip],
                    capture_output=True,
                    timeout=5
                )
                ping_success = result.returncode == 0
            except Exception:
                ping_success = False
            
            # Проверка доступных экспортов (если доступна команда showmount)
            exports = None
            try:
                result = subprocess.run(
                    ['showmount', '-e', server_ip],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    exports = result.stdout.strip()
            except Exception:
                pass
            
            return jsonify({
                'status': 'success',
                'server': server_ip,
                'ping_available': ping_success,
                'exports': exports
            }), 200
                
        except Exception as e:
            logger.error(f"Error testing NFS: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Error testing NFS: {str(e)}'
            }), 500


def _mount_nfs_with_sudo(nfs_server: str, mount_point: str, nfs_options: str = None) -> tuple:
    """
    Монтирование NFS с использованием sudo (если доступен) или напрямую
    
    Returns:
        Tuple (success, message)
    """
    if not nfs_options:
        nfs_options = "vers=4.1,soft,timeo=30,retrans=3,noatime"
    
    # Сначала пробуем без sudo (если приложение запущено от root)
    success, message = mount_nfs(nfs_server, mount_point, nfs_options)
    
    if success:
        return True, message
    
    # Если не получилось, пробуем с sudo
    try:
        cmd = ['sudo', 'mount', '-t', 'nfs', '-o', nfs_options, nfs_server, mount_point]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            return True, "NFS успешно смонтирована"
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            # Если sudo требует пароль, возвращаем понятное сообщение
            if 'password' in error_msg.lower() or 'sudo' in error_msg.lower():
                return False, "Требуются права root. Настройте sudo без пароля для пользователя приложения или запустите приложение от root."
            return False, f"Ошибка монтирования: {error_msg}"
    except FileNotFoundError:
        return False, "Команда sudo недоступна"
    except subprocess.TimeoutExpired:
        return False, "Таймаут при монтировании NFS"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"


def _create_directory_with_sudo(mount_point: str, permissions: int = 0o755) -> tuple:
    """
    Создание директории с использованием sudo (если доступен) или напрямую
    
    Returns:
        Tuple (success, message)
    """
    from pathlib import Path
    
    mount_path = Path(mount_point)
    
    # Если директория уже существует
    if mount_path.exists():
        if mount_path.is_dir():
            return True, f"Directory already exists: {mount_point}"
        else:
            return False, f"Path exists but is not a directory: {mount_point}"
    
    # Пробуем создать напрямую
    try:
        mount_path.mkdir(parents=True, exist_ok=True)
        mount_path.chmod(permissions)
        return True, f"Directory created successfully: {mount_point}"
    except PermissionError:
        # Если нет прав, пробуем с sudo
        pass
    except Exception as e:
        # Другие ошибки
        pass
    
    # Пробуем с sudo
    try:
        # Создаем директорию через sudo
        result = subprocess.run(
            ['sudo', 'mkdir', '-p', mount_point],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Устанавливаем права доступа через sudo
            perm_str = oct(permissions)[2:]  # Преобразуем 0o755 -> 755
            chmod_result = subprocess.run(
                ['sudo', 'chmod', perm_str, mount_point],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if chmod_result.returncode == 0:
                return True, f"Directory created successfully via sudo: {mount_point}"
            else:
                return True, f"Directory created but failed to set permissions: {mount_point}"
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            if 'password' in error_msg.lower():
                return False, "Требуются права root. Настройте sudo без пароля или запустите приложение от root."
            return False, f"Ошибка создания директории: {error_msg}"
    except FileNotFoundError:
        return False, "Команда sudo недоступна"
    except subprocess.TimeoutExpired:
        return False, "Таймаут при создании директории"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"


def _unmount_nfs_with_sudo(mount_point: str) -> tuple:
    """
    Размонтирование NFS с использованием sudo (если доступен)
    
    Returns:
        Tuple (success, message)
    """
    # Проверяем, смонтирована ли
    if not check_nfs_mounted(mount_point):
        return True, "NFS не смонтирована"
    
    # Пробуем размонтировать без sudo
    try:
        result = subprocess.run(
            ['umount', mount_point],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, "NFS успешно размонтирована"
    except Exception:
        pass
    
    # Пробуем с sudo
    try:
        result = subprocess.run(
            ['sudo', 'umount', mount_point],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, "NFS успешно размонтирована"
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            if 'password' in error_msg.lower():
                return False, "Требуются права root для размонтирования"
            return False, f"Ошибка размонтирования: {error_msg}"
    except FileNotFoundError:
        return False, "Команда sudo недоступна"
    except Exception as e:
        return False, f"Ошибка: {str(e)}"

