"""
API маршруты для работы с конфигурацией
"""

import os
from flask import Flask, jsonify, request
from typing import Dict, Any, Tuple
from flask_login import login_required, current_user

from app.utils.user_config import (
    get_user_config, save_user_config, list_user_configs, 
    create_user_config, delete_user_config, set_default_config
)
from app.utils.config_manager import AppConfig


def init_routes(app: Flask) -> None:
    """Инициализация маршрутов конфигурации"""
    
    @app.route('/api/config', methods=['GET', 'POST'])
    @login_required
    def api_config():
        """API для работы с персональной конфигурацией пользователя"""
        if request.method == 'POST':
            return _handle_config_update(app)
        else:
            return _handle_config_get()
    
    @app.route('/api/config/list', methods=['GET'])
    @login_required
    def api_config_list():
        """API для получения списка всех конфигураций пользователя"""
        try:
            configs = list_user_configs(user_id=current_user.id)
            return jsonify({'status': 'success', 'configs': configs}), 200
        except Exception as e:
            app.logger.error(f"Error listing configs: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/config/create', methods=['POST'])
    @login_required
    def api_config_create():
        """API для создания новой конфигурации"""
        try:
            data = request.get_json() or {}
            name = data.get('name', '').strip()
            
            if not name:
                return jsonify({'status': 'error', 'message': 'Configuration name is required'}), 400
            
            config_data = data.get('config', {})
            is_default = data.get('is_default', False)
            
            user_config = create_user_config(
                name=name,
                config=config_data,
                user_id=current_user.id,
                is_default=is_default
            )
            
            return jsonify({
                'status': 'success',
                'message': f'Configuration "{name}" created successfully',
                'config_id': user_config.id
            }), 201
            
        except ValueError as e:
            return jsonify({'status': 'error', 'message': str(e)}), 400
        except Exception as e:
            app.logger.error(f"Error creating config: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/config/<int:config_id>', methods=['GET', 'DELETE', 'PATCH'])
    @login_required
    def api_config_by_id(config_id: int):
        """API для работы с конкретной конфигурацией"""
        try:
            if request.method == 'GET':
                # Получить конфигурацию
                user_config = get_user_config(user_id=current_user.id, config_id=config_id)
                if user_config:
                    config_dict = user_config.to_dict()
                    # Добавляем информацию о конфиге
                    from app.db import session_scope
                    from app.models.db_models import UserConfig
                    with session_scope() as session:
                        db_config = session.query(UserConfig).filter(
                            UserConfig.id == config_id,
                            UserConfig.user_id == current_user.id
                        ).first()
                        if db_config:
                            config_dict['CONFIG_ID'] = db_config.id
                            config_dict['CONFIG_NAME'] = db_config.name
                            config_dict['IS_DEFAULT'] = db_config.is_default
                    
                    return jsonify({'status': 'success', 'config': config_dict}), 200
                else:
                    return jsonify({'status': 'error', 'message': 'Configuration not found'}), 404
            
            elif request.method == 'DELETE':
                # Удалить конфигурацию
                try:
                    delete_user_config(config_id=config_id, user_id=current_user.id)
                    return jsonify({'status': 'success', 'message': 'Configuration deleted successfully'}), 200
                except ValueError as e:
                    return jsonify({'status': 'error', 'message': str(e)}), 400
            
            elif request.method == 'PATCH':
                # Обновить конфигурацию
                data = request.get_json() or {}
                
                # Обновление названия конфига
                if 'name' in data:
                    new_name = data.get('name', '').strip()
                    if new_name:
                        config_data = {'CONFIG_NAME': new_name}
                        save_user_config(config_data, user_id=current_user.id, config_id=config_id)
                
                # Установка конфига по умолчанию
                if 'is_default' in data and data.get('is_default'):
                    set_default_config(config_id=config_id, user_id=current_user.id)
                
                # Обновление параметров конфига
                if 'config' in data:
                    save_user_config(data['config'], user_id=current_user.id, config_id=config_id)
                
                return jsonify({'status': 'success', 'message': 'Configuration updated successfully'}), 200
            
        except Exception as e:
            app.logger.error(f"Error handling config {config_id}: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    @app.route('/api/config/set-default', methods=['POST'])
    @login_required
    def api_config_set_default():
        """API для установки конфигурации по умолчанию"""
        try:
            data = request.get_json() or {}
            config_id = data.get('config_id')
            config_name = data.get('config_name')
            
            if not config_id and not config_name:
                return jsonify({'status': 'error', 'message': 'config_id or config_name is required'}), 400
            
            success = set_default_config(
                config_id=config_id,
                config_name=config_name,
                user_id=current_user.id
            )
            
            if success:
                return jsonify({'status': 'success', 'message': 'Default configuration updated'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Configuration not found'}), 404
                
        except Exception as e:
            app.logger.error(f"Error setting default config: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def _handle_config_update(app: Flask) -> Tuple[Dict[str, Any], int]:
        """Обработка обновления персональной конфигурации пользователя"""
        try:
            config_data = request.get_json()
            app.logger.info(f"Received config update from user {current_user.username}: {list(config_data.keys()) if config_data else 'No data'}")
            
            # Логируем длину S3 credentials (без значений для безопасности)
            if config_data:
                s3_access_key_len = len(str(config_data.get('S3_ACCESS_KEY', '')))
                s3_secret_key_len = len(str(config_data.get('S3_SECRET_KEY', '')))
                app.logger.info(
                    f"S3 credentials from form: "
                    f"S3_ACCESS_KEY length={s3_access_key_len}, "
                    f"S3_SECRET_KEY length={s3_secret_key_len}"
                )
            
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
            
            # Валидация S3 credentials (должны быть указаны)
            s3_credentials_required = ['S3_ACCESS_KEY', 'S3_SECRET_KEY']
            missing_credentials = [field for field in s3_credentials_required
                                 if field not in config_data or not config_data[field] or not config_data[field].strip()]
            
            if missing_credentials:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing S3 credentials: {", ".join(missing_credentials)}. Please provide S3 Access Key and Secret Key.'
                }), 400
            
            # Проверяем существование NFS пути
            nfs_path = config_data['NFS_PATH']
            if not os.path.exists(nfs_path):
                return jsonify({
                    'status': 'error', 
                    'message': f'NFS path does not exist: {nfs_path}'
                }), 400
            
            # Определяем, какой конфиг обновлять
            config_id = config_data.pop('CONFIG_ID', None)
            config_name = config_data.pop('CONFIG_NAME', None)
            
            # Сохраняем персональную конфигурацию пользователя
            save_user_config(
                config_data, 
                user_id=current_user.id,
                config_id=config_id,
                config_name=config_name
            )
            app.logger.info(f"User {current_user.username} configuration updated successfully (config_id={config_id}, config_name={config_name})")
            
            # Возвращаем обновленную конфигурацию
            user_config = get_user_config(
                user_id=current_user.id,
                config_id=config_id,
                config_name=config_name
            )
            if user_config:
                config_dict = user_config.to_dict()
                # Логируем длину сохраненных credentials
                saved_access_key_len = len(str(config_dict.get('S3_ACCESS_KEY', '')))
                saved_secret_key_len = len(str(config_dict.get('S3_SECRET_KEY', '')))
                app.logger.info(
                    f"Configuration saved successfully. "
                    f"Saved S3_ACCESS_KEY length={saved_access_key_len}, "
                    f"S3_SECRET_KEY length={saved_secret_key_len}"
                )
                return jsonify({
                    'status': 'success', 
                    'message': 'Configuration updated successfully',
                    'config': config_dict
                }), 200
            else:
                return jsonify({'status': 'error', 'message': 'Failed to retrieve updated config'}), 500
            
        except Exception as e:
            app.logger.error(f"Error updating configuration: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': f'Error updating configuration: {e}'}), 500
    
    def _handle_config_get() -> Tuple[Dict[str, Any], int]:
        """Обработка получения персональной конфигурации пользователя"""
        try:
            # Проверяем, указан ли config_id в query параметрах
            config_id = request.args.get('config_id', type=int)
            config_name = request.args.get('config_name', type=str)
            
            user_config = get_user_config(
                user_id=current_user.id,
                config_id=config_id,
                config_name=config_name
            )
            
            if user_config:
                config_dict = user_config.to_dict()
                
                # Добавляем информацию о конфиге, если загружен конкретный
                if config_id or config_name:
                    from app.db import session_scope
                    from app.models.db_models import UserConfig
                    with session_scope() as session:
                        query = session.query(UserConfig).filter(UserConfig.user_id == current_user.id)
                        if config_id:
                            db_config = query.filter(UserConfig.id == config_id).first()
                        else:
                            db_config = query.filter(UserConfig.name == config_name).first()
                        
                        if db_config:
                            config_dict['CONFIG_ID'] = db_config.id
                            config_dict['CONFIG_NAME'] = db_config.name
                            config_dict['IS_DEFAULT'] = db_config.is_default
                
                return jsonify(config_dict), 200
            else:
                # Если конфигурации нет, возвращаем дефолтную
                default_config = AppConfig()
                return jsonify(default_config.to_dict()), 200
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error getting user config: {e}", exc_info=True)
            # Возвращаем дефолтную конфигурацию в случае ошибки
            default_config = AppConfig()
            return jsonify(default_config.to_dict()), 200

