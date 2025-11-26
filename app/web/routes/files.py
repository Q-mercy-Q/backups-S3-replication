"""
API маршруты для просмотра файлов исходной директории
"""

import os
from pathlib import Path
from datetime import datetime
from typing import TYPE_CHECKING

import humanize
from flask import Flask, jsonify, request

from app.utils.config import get_nfs_path

if TYPE_CHECKING:
    from flask_socketio import SocketIO


def init_routes(app: Flask) -> None:
    """Инициализация маршрутов просмотра файлов"""

    @app.route('/api/files', methods=['GET'])
    def api_list_files():
        """API для получения списка файлов в директории"""
        base_path = Path(get_nfs_path()).resolve()
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

