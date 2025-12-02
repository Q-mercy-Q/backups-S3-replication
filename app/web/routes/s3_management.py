"""
API маршруты для расширенного управления S3 хранилищем
"""

from flask import Flask, jsonify, request
from typing import Dict, Any, Tuple
import json

from flask_login import login_required, current_user

from app.services.s3_management import (
    list_all_buckets,
    create_bucket,
    delete_bucket,
    get_bucket_info,
    set_bucket_versioning,
    set_bucket_lifecycle,
    set_bucket_cors,
    set_bucket_policy,
    set_bucket_tags,
    get_bucket_statistics,
    list_iam_users,
    create_iam_user,
    delete_iam_user,
    list_user_access_keys,
    create_access_key,
    delete_access_key
)


def init_routes(app: Flask) -> None:
    """Инициализация маршрутов управления S3"""
    
    @app.route('/api/s3-management/buckets', methods=['GET'])
    @login_required
    def api_list_buckets():
        """API для получения списка всех бакетов"""
        try:
            buckets = list_all_buckets(user_id=current_user.id)
            return jsonify({
                'status': 'success',
                'buckets': buckets
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/s3-management/buckets', methods=['POST'])
    @login_required
    def api_create_bucket():
        """API для создания нового бакета"""
        try:
            data = request.get_json()
            bucket_name = data.get('name')
            location = data.get('location', 'us-east-1')
            
            if not bucket_name:
                return jsonify({
                    'status': 'error',
                    'message': 'Bucket name is required'
                }), 400
            
            success = create_bucket(bucket_name, location, user_id=current_user.id)
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': f'Bucket {bucket_name} created successfully'
                }), 201
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Bucket {bucket_name} already exists'
                }), 409
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/s3-management/buckets/<bucket_name>', methods=['DELETE'])
    @login_required
    def api_delete_bucket(bucket_name: str):
        """API для удаления бакета"""
        try:
            data = request.get_json() or {}
            force = data.get('force', False)
            
            success = delete_bucket(bucket_name, force=force, user_id=current_user.id)
            
            if success:
                return jsonify({
                    'status': 'success',
                    'message': f'Bucket {bucket_name} deleted successfully'
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'Bucket {bucket_name} does not exist'
                }), 404
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/s3-management/buckets/<bucket_name>', methods=['GET'])
    @login_required
    def api_get_bucket_info(bucket_name: str):
        """API для получения информации о бакете"""
        try:
            info = get_bucket_info(bucket_name, user_id=current_user.id)
            return jsonify({
                'status': 'success',
                'bucket': info
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/s3-management/buckets/<bucket_name>/statistics', methods=['GET'])
    @login_required
    def api_get_bucket_statistics(bucket_name: str):
        """API для получения статистики бакета"""
        try:
            stats = get_bucket_statistics(bucket_name, user_id=current_user.id)
            return jsonify({
                'status': 'success',
                'statistics': stats
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/s3-management/buckets/<bucket_name>/versioning', methods=['PUT'])
    @login_required
    def api_set_bucket_versioning(bucket_name: str):
        """API для установки версионирования бакета"""
        try:
            data = request.get_json()
            enabled = data.get('enabled', False)
            mfa_delete = data.get('mfa_delete', False)
            
            success = set_bucket_versioning(
                bucket_name,
                enabled=enabled,
                mfa_delete=mfa_delete,
                user_id=current_user.id
            )
            
            return jsonify({
                'status': 'success',
                'message': f'Versioning {"enabled" if enabled else "disabled"} for bucket {bucket_name}'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/s3-management/buckets/<bucket_name>/lifecycle', methods=['PUT'])
    @login_required
    def api_set_bucket_lifecycle(bucket_name: str):
        """API для установки lifecycle policy бакета"""
        try:
            data = request.get_json()
            rules = data.get('rules', [])
            
            success = set_bucket_lifecycle(
                bucket_name,
                rules=rules,
                user_id=current_user.id
            )
            
            return jsonify({
                'status': 'success',
                'message': f'Lifecycle policy set for bucket {bucket_name}'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/s3-management/buckets/<bucket_name>/cors', methods=['PUT'])
    @login_required
    def api_set_bucket_cors(bucket_name: str):
        """API для установки CORS правил бакета"""
        try:
            data = request.get_json()
            cors_rules = data.get('cors_rules', [])
            
            success = set_bucket_cors(
                bucket_name,
                cors_rules=cors_rules,
                user_id=current_user.id
            )
            
            return jsonify({
                'status': 'success',
                'message': f'CORS rules set for bucket {bucket_name}'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/s3-management/buckets/<bucket_name>/policy', methods=['PUT'])
    @login_required
    def api_set_bucket_policy(bucket_name: str):
        """API для установки bucket policy"""
        try:
            data = request.get_json()
            policy = data.get('policy')
            
            if not policy:
                return jsonify({
                    'status': 'error',
                    'message': 'Policy is required'
                }), 400
            
            success = set_bucket_policy(
                bucket_name,
                policy=policy,
                user_id=current_user.id
            )
            
            return jsonify({
                'status': 'success',
                'message': f'Policy set for bucket {bucket_name}'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @app.route('/api/s3-management/buckets/<bucket_name>/tags', methods=['PUT'])
    @login_required
    def api_set_bucket_tags(bucket_name: str):
        """API для установки тегов бакета"""
        try:
            data = request.get_json()
            tags = data.get('tags', {})
            
            success = set_bucket_tags(
                bucket_name,
                tags=tags,
                user_id=current_user.id
            )
            
            return jsonify({
                'status': 'success',
                'message': f'Tags set for bucket {bucket_name}'
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    # NOTE: IAM / Users & Access Keys API endpoints are disabled in this deployment.

