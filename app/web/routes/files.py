"""
API маршруты для просмотра файлов исходной директории
"""

import os
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING

import humanize
from flask import Flask, jsonify, request
from flask_login import login_required

from app.utils.config import get_nfs_path

if TYPE_CHECKING:
    from flask_socketio import SocketIO


def init_routes(app: Flask) -> None:
    """Инициализация маршрутов просмотра файлов"""

    @app.route('/api/files', methods=['GET'])
    @login_required
    def api_list_files():
        """API для получения списка файлов в директории"""
        from flask_login import current_user
        from app.utils.config import get_nfs_path
        base_path = Path(get_nfs_path(user_id=current_user.id)).resolve()
        requested_path = request.args.get('path', '.')

        try:
            target_path = (base_path / requested_path).resolve()
        except Exception:
            return jsonify({'status': 'error', 'message': 'Invalid path'}), 400

        if not str(target_path).startswith(str(base_path)):
            return jsonify({'status': 'error', 'message': 'Path is outside the allowed directory'}), 400

        if not target_path.exists():
            return jsonify({'status': 'error', 'message': 'Path does not exist'}), 404

        entries = []
        try:
            for entry in sorted(target_path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))[:500]:
                stat = entry.stat()
                relative_path = '.' if entry == base_path else str(entry.relative_to(base_path))
                entries.append({
                    'name': entry.name,
                    'type': 'directory' if entry.is_dir() else 'file',
                    'size': stat.st_size if entry.is_file() else None,
                    'size_human': humanize.naturalsize(stat.st_size) if entry.is_file() else None,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'relative_path': relative_path
                })
        except PermissionError:
            return jsonify({'status': 'error', 'message': 'Permission denied'}), 403

        relative_current = '.' if target_path == base_path else str(target_path.relative_to(base_path))
        parent_path = None
        if target_path != base_path:
            parent = target_path.parent
            parent_path = '.' if parent == base_path else str(parent.relative_to(base_path))

        return jsonify({
            'status': 'success',
            'path': relative_current,
            'parent': parent_path,
            'entries': entries
        }), 200
    
    @app.route('/api/files/scan', methods=['GET'])
    @login_required
    def api_scan_files_with_filters():
        """API для расширенного сканирования файлов с фильтрами"""
        from flask_login import current_user
        from app.services.s3_client import get_existing_s3_files
        from app.services.file_scanner import scan_backup_files
        
        try:
            # Получаем параметры фильтрации
            file_extensions = request.args.getlist('extensions')
            categories = request.args.getlist('categories')
            min_size = request.args.get('min_size', type=int)
            max_size = request.args.get('max_size', type=int)
            skip_time_filter = request.args.get('skip_time', 'false').lower() == 'true'
            backup_days = request.args.get('backup_days', type=int)
            
            # Если extensions пуст, делаем None
            if not file_extensions:
                file_extensions = None
            
            # Если categories пуст, делаем None
            if not categories:
                categories = None
            
            # Получаем существующие файлы
            existing_files = get_existing_s3_files(user_id=current_user.id)
            
            # Сканируем файлы с фильтрами
            files = scan_backup_files(
                existing_s3_files=existing_files,
                categories=categories,
                user_id=current_user.id,
                file_extensions=file_extensions,
                min_size=min_size,
                max_size=max_size,
                skip_time_filter=skip_time_filter,
                backup_days=backup_days
            )
            
            # Формируем результат
            result_files = []
            total_size = 0
            for full_path, rel_path, tag, file_size in files:
                result_files.append({
                    'path': rel_path,
                    'full_path': full_path,
                    'tag': tag,
                    'size': file_size,
                    'size_human': humanize.naturalsize(file_size)
                })
                total_size += file_size
            
            return jsonify({
                'status': 'success',
                'files': result_files,
                'count': len(result_files),
                'total_size': total_size,
                'total_size_human': humanize.naturalsize(total_size)
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error scanning files with filters: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Error scanning files: {str(e)}'
            }), 500
    
    @app.route('/api/files/scan-specific', methods=['POST'])
    @login_required
    def api_scan_specific_files():
        """API для сканирования конкретных файлов"""
        from flask_login import current_user
        from app.services.s3_client import get_existing_s3_files
        from app.services.file_scanner import scan_specific_files
        
        try:
            data = request.get_json() or {}
            file_paths = data.get('file_paths', [])
            
            if not file_paths:
                return jsonify({
                    'status': 'error',
                    'message': 'file_paths is required'
                }), 400
            
            if not isinstance(file_paths, list):
                return jsonify({
                    'status': 'error',
                    'message': 'file_paths must be a list'
                }), 400
            
            # Получаем существующие файлы
            existing_files = get_existing_s3_files(user_id=current_user.id)
            
            # Сканируем конкретные файлы
            files = scan_specific_files(
                file_paths=file_paths,
                existing_s3_files=existing_files,
                user_id=current_user.id
            )
            
            # Формируем результат
            result_files = []
            total_size = 0
            for full_path, rel_path, tag, file_size in files:
                result_files.append({
                    'path': rel_path,
                    'full_path': full_path,
                    'tag': tag,
                    'size': file_size,
                    'size_human': humanize.naturalsize(file_size)
                })
                total_size += file_size
            
            return jsonify({
                'status': 'success',
                'files': result_files,
                'count': len(result_files),
                'total_size': total_size,
                'total_size_human': humanize.naturalsize(total_size)
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error scanning specific files: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Error scanning files: {str(e)}'
            }), 500

