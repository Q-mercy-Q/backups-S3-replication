"""
Admin dashboard routes and APIs
"""

from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required

from app.auth.decorators import admin_required
from app.auth.utils import create_user, get_user_by_username, verify_password
from app.db import session_scope
from app.models.db_models import User


def init_routes(app):
    admin_bp = Blueprint("admin_api", __name__)

    @app.route("/admin")
    @login_required
    @admin_required
    def admin_dashboard():
        return render_template("admin.html")

    @admin_bp.route("/users", methods=["GET", "POST"])
    @login_required
    @admin_required
    def manage_users():
        if request.method == "GET":
            with session_scope() as session:
                users = session.query(User).order_by(User.created_at.desc()).all()
                payload = [
                    {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "is_active": user.is_active,
                        "is_admin": user.is_admin,
                        "created_at": user.created_at.isoformat() if user.created_at else None,
                    }
                    for user in users
                ]
                return jsonify({"status": "success", "users": payload})

        data = request.get_json() or {}
        username = (data.get("username") or "").strip()
        password = data.get("password") or ""
        email = (data.get("email") or "").strip() or None
        is_admin = bool(data.get("is_admin"))

        if not username or not password:
            return jsonify({"status": "error", "message": "Username and password are required"}), 400
        
        if len(password) < 8:
            return jsonify({"status": "error", "message": "Password must be at least 8 characters long"}), 400
        
        if len(username) < 3:
            return jsonify({"status": "error", "message": "Username must be at least 3 characters long"}), 400

        # Проверка на существующего пользователя
        existing_user = get_user_by_username(username)
        if existing_user:
            return jsonify({"status": "error", "message": f"User '{username}' already exists"}), 400

        # Проверка email, если указан
        if email:
            with session_scope() as session:
                existing_email = session.query(User).filter(User.email == email).first()
                if existing_email:
                    return jsonify({"status": "error", "message": f"Email '{email}' is already in use"}), 400

        try:
            user = create_user(username=username, password=password, email=email, is_admin=is_admin)
            # Получаем пользователя заново из БД, чтобы убедиться, что все поля доступны
            created_user = get_user_by_username(username)
            if not created_user:
                return jsonify({"status": "error", "message": "User was created but could not be retrieved"}), 500
        except Exception as exc:
            error_msg = str(exc)
            return jsonify({"status": "error", "message": f"Failed to create user: {error_msg}"}), 400

        return jsonify(
            {
                "status": "success",
                "user": {
                    "id": created_user.id,
                    "username": created_user.username,
                    "email": created_user.email,
                    "is_active": created_user.is_active,
                    "is_admin": created_user.is_admin,
                    "created_at": created_user.created_at.isoformat() if created_user.created_at else None,
                },
            }
        ), 201

    @admin_bp.route("/users/<int:user_id>", methods=["PATCH", "DELETE"])
    @login_required
    @admin_required
    def update_user(user_id: int):
        from flask_login import current_user
        
        if request.method == "DELETE":
            # Проверка, что нельзя удалить самого себя
            if user_id == current_user.id:
                return jsonify({"status": "error", "message": "You cannot delete your own account"}), 400
            
            with session_scope() as session:
                user = session.get(User, user_id)
                if not user:
                    return jsonify({"status": "error", "message": "User not found"}), 404
                
                username = user.username
                
                # Удаляем конфигурацию пользователя, если она существует
                from app.models.db_models import UserConfig
                user_config = session.query(UserConfig).filter(UserConfig.user_id == user_id).first()
                if user_config:
                    session.delete(user_config)
                
                # Удаляем пользователя
                session.delete(user)
                
                return jsonify({
                    "status": "success",
                    "message": f"User '{username}' deleted successfully"
                }), 200
        
        # PATCH - обновление пользователя
        data = request.get_json() or {}
        with session_scope() as session:
            user = session.get(User, user_id)
            if not user:
                return jsonify({"status": "error", "message": "User not found"}), 404

            if "is_active" in data:
                user.is_active = bool(data["is_active"])
            if "is_admin" in data:
                user.is_admin = bool(data["is_admin"])
            if "password" in data and data["password"]:
                if len(data["password"]) < 8:
                    return jsonify({"status": "error", "message": "Password must be at least 8 characters long"}), 400
                from werkzeug.security import generate_password_hash
                user.password_hash = generate_password_hash(data["password"])

            session.add(user)
            session.flush()
            session.refresh(user)

            return jsonify(
                {
                    "status": "success",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "is_active": user.is_active,
                        "is_admin": user.is_admin,
                    },
                }
            )

    app.register_blueprint(admin_bp, url_prefix="/api/admin")

