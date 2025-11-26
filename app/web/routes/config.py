"""
API маршруты для работы с конфигурацией
"""

import os
from flask import Flask, jsonify, request
from typing import Dict, Any, Tuple

from app.utils.config import get_config, update_config


def init_routes(app: Flask) -> None:
    """Инициализация маршрутов конфигурации"""
    
    @app.route('/api/config', methods=['GET', 'POST'])
    def api_config():
        """API для работы с конфигурацией"""
        if request.method == 'POST':
            return _handle_config_update(app)
        else:
            return _handle_config_get()
    
    def _handle_config_update(app: Flask) -> Tuple[Dict[str, Any], int]:
        """Обработка обновления конфигурации"""
        try:
            config_data = request.get_json()
            app.logger.info(f"Received config update: {list(config_data.keys()) if config_data else 'No data'}")
            
            if not config_data:
                return jsonify({'status': 'error', 'message': 'No JSON data provided'}), 400
            
            # Валидация обязательных полей
            required_fields = ['NFS_PATH', 'S3_ENDPOINT', 'S3_BUCKET']
            missing_fields = [field for field in required_fields 
                            if field not in config_data or not config_data[field]]
            
            if missing_fields:
                return jsonify({
                    'status': 'error', 
                    'message': f'Missing required fields: {", ".join(missing_fields)}'
                }), 400
            
            # Проверяем существование NFS пути
            nfs_path = config_data['NFS_PATH']
            if not os.path.exists(nfs_path):
                return jsonify({
                    'status': 'error', 
                    'message': f'NFS path does not exist: {nfs_path}'
                }), 400
            
            # Обновляем конфигурацию
            update_config(config_data)
            app.logger.info("Configuration updated successfully")
            
            # Возвращаем обновленную конфигурацию
            return jsonify({
                'status': 'success', 
                'message': 'Configuration updated successfully',
                'config': get_config()
            }), 200
            
        except Exception as e:
            app.logger.error(f"Error updating configuration: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': f'Error updating configuration: {e}'}), 500
    
    def _handle_config_get() -> Tuple[Dict[str, Any], int]:
        """Обработка получения конфигурации"""
        return jsonify(get_config()), 200

