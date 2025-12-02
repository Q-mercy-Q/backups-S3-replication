"""
API маршруты для просмотра и навигации по S3 бакету
"""

import logging
from flask import Flask, jsonify, request
from flask_login import login_required, current_user

from app.services.s3_browser import list_bucket_objects, get_bucket_stats, get_object_info, delete_bucket_object, delete_bucket_directory
from app.utils.config import get_s3_bucket

logger = logging.getLogger(__name__)


def init_routes(app: Flask) -> None:
    """Инициализация маршрутов просмотра S3 бакета"""
    
    @app.route('/api/s3/browser', methods=['GET'])
    @login_required
    def api_list_s3_objects():
        """API для получения списка объектов в S3 бакете"""
        try:
            # Получаем параметры запроса
            prefix = request.args.get('prefix', '').strip()
            recursive = request.args.get('recursive', 'false').lower() == 'true'
            
            # Декодируем prefix (на случай если пришёл в URL-encoded виде)
            if prefix:
                prefix = prefix.replace('%2F', '/')
                # Убираем начальный / если есть
                if prefix.startswith('/'):
                    prefix = prefix[1:]
            
            # Получаем объекты бакета
            objects = list_bucket_objects(
                prefix=prefix,
                recursive=recursive,
                user_id=current_user.id
            )
            
            # Формируем путь для навигации
            current_path = prefix if prefix else '.'
            
            # Определяем родительский путь
            parent_path = None
            if prefix:
                parts = prefix.rstrip('/').split('/')
                if len(parts) > 1:
                    parent_path = '/'.join(parts[:-1])
                elif parts[0]:
                    parent_path = ''
                else:
                    parent_path = None
            else:
                parent_path = None
            
            # Получаем статистику для текущего уровня (если нужно)
            stats = None
            if request.args.get('include_stats', 'false').lower() == 'true':
                stats = get_bucket_stats(prefix=prefix, user_id=current_user.id)
            
            return jsonify({
                'status': 'success',
                'bucket': get_s3_bucket(user_id=current_user.id),
                'path': current_path,
                'parent': parent_path if parent_path is not None else None,
                'entries': objects,
                'stats': stats,
                'count': len(objects)
            }), 200
            
        except Exception as e:
            logger.error(f"Error listing S3 objects: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Error listing S3 objects: {str(e)}'
            }), 500
    
    @app.route('/api/s3/browser/object', methods=['GET'])
    @login_required
    def api_get_s3_object_info():
        """API для получения информации об объекте"""
        try:
            object_path = request.args.get('path', '').strip()
            
            if not object_path:
                return jsonify({
                    'status': 'error',
                    'message': 'Object path is required'
                }), 400
            
            # Декодируем путь
            object_path = object_path.replace('%2F', '/')
            if object_path.startswith('/'):
                object_path = object_path[1:]
            
            # Получаем информацию об объекте
            object_info = get_object_info(object_path, user_id=current_user.id)
            
            if object_info is None:
                return jsonify({
                    'status': 'error',
                    'message': 'Object not found'
                }), 404
            
            return jsonify({
                'status': 'success',
                'object': object_info
            }), 200
            
        except Exception as e:
            logger.error(f"Error getting S3 object info: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Error getting object info: {str(e)}'
            }), 500
    
    @app.route('/api/s3/browser/stats', methods=['GET'])
    @login_required
    def api_get_s3_stats():
        """API для получения статистики бакета или конкретной директории"""
        try:
            prefix = request.args.get('prefix', '').strip()
            directory_path = request.args.get('directory', '').strip()
            
            # Если указана директория, возвращаем статистику для нее
            if directory_path:
                directory_path = directory_path.replace('%2F', '/')
                if directory_path.startswith('/'):
                    directory_path = directory_path[1:]
                
                from app.services.s3_browser import _get_directory_stats_fast
                from app.services.s3_client import get_minio_client
                from app.utils.config import get_s3_bucket
                
                minio_client = get_minio_client(user_id=current_user.id)
                bucket_name = get_s3_bucket(user_id=current_user.id)
                
                dir_stats = _get_directory_stats_fast(directory_path + '/', minio_client, bucket_name)
                
                return jsonify({
                    'status': 'success',
                    'stats': {
                        'total_size': dir_stats.get('total_size', 0),
                        'total_size_human': dir_stats.get('total_size_human', '0 B'),
                        'file_count': dir_stats.get('file_count', 0),
                        'last_modified': dir_stats.get('last_modified')
                    }
                }), 200
            
            # Иначе возвращаем общую статистику бакета
            if prefix:
                prefix = prefix.replace('%2F', '/')
                if prefix.startswith('/'):
                    prefix = prefix[1:]
            
            stats = get_bucket_stats(prefix=prefix, user_id=current_user.id)
            
            return jsonify({
                'status': 'success',
                'stats': stats
            }), 200
            
        except Exception as e:
            logger.error(f"Error getting S3 stats: {e}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Error getting stats: {str(e)}'
            }), 500
    
    @app.route('/api/s3/browser/delete', methods=['POST'])
    @login_required
    def api_delete_s3_object():
        """API для удаления объекта или директории из S3 бакета"""
        try:
            data = request.get_json()
            object_path = data.get('path', '').strip()
            is_directory = data.get('is_directory', False)
            
            if not object_path:
                return jsonify({'status': 'error', 'message': 'Object path is required'}), 400
            
            # Декодируем путь, если нужно
            object_path = object_path.replace('%2F', '/')
            if object_path.startswith('/'):
                object_path = object_path[1:]
            
            # Удаляем объект или директорию
            if is_directory:
                deleted_count, error_count = delete_bucket_directory(object_path, user_id=current_user.id)
                if error_count == 0:
                    logger.info(f"Directory deleted by user {current_user.username}: {object_path} ({deleted_count} objects)")
                    return jsonify({
                        'status': 'success', 
                        'message': f'Directory deleted successfully ({deleted_count} objects removed)',
                        'deleted_count': deleted_count
                    }), 200
                elif deleted_count > 0:
                    return jsonify({
                        'status': 'partial',
                        'message': f'Directory partially deleted ({deleted_count} objects removed, {error_count} errors)',
                        'deleted_count': deleted_count,
                        'error_count': error_count
                    }), 200
                else:
                    return jsonify({
                        'status': 'error',
                        'message': 'Failed to delete directory',
                        'error_count': error_count
                    }), 500
            else:
                success = delete_bucket_object(object_path, user_id=current_user.id)
                if success:
                    logger.info(f"Object deleted by user {current_user.username}: {object_path}")
                    return jsonify({'status': 'success', 'message': f'Object deleted successfully'}), 200
                else:
                    return jsonify({'status': 'error', 'message': 'Failed to delete object'}), 500
                
        except Exception as e:
            logger.error(f"Error deleting object: {e}", exc_info=True)
            return jsonify({'status': 'error', 'message': f'Error deleting object: {str(e)}'}), 500


