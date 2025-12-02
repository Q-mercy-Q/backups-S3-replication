from flask import Blueprint, redirect, render_template, request, url_for, flash, jsonify
from flask_login import current_user, login_required, login_user, logout_user

from app.auth import login_manager
from app.auth.utils import create_user, get_user_by_username, users_exist, verify_password
from app.db import session_scope
from app.models.db_models import User

auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id: str):
    try:
        with session_scope() as session:
            return session.get(User, int(user_id))
    except Exception:
        return None


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    registration_open = not users_exist()

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_user_by_username(username)
        if not user or not verify_password(user.password_hash, password):
            flash("Invalid username or password", "danger")
            return render_template("login.html", registration_open=registration_open)
        if not user.is_active:
            flash("Account is disabled. Contact administrator.", "warning")
            return render_template("login.html", registration_open=registration_open)
        login_user(user, remember=True)
        next_page = request.args.get("next") or url_for("index")
        return redirect(next_page)

    return render_template("login.html", registration_open=registration_open)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    registration_open = not users_exist()
    if not registration_open:
        if not current_user.is_authenticated or not current_user.is_admin:
            return redirect(url_for("auth.login"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip() or None

        if not username or not password:
            flash("Username and password are required", "danger")
            return render_template("register.html", registration_open=registration_open)

        existing = get_user_by_username(username)
        if existing:
            flash("User with this username already exists", "danger")
            return render_template("register.html", registration_open=registration_open)

        new_user = create_user(
            username=username,
            password=password,
            email=email,
            is_admin=True if not users_exist() else False,
        )

        flash("User created successfully", "success")
        if not current_user.is_authenticated:
            login_user(new_user)
            return redirect(url_for("index"))
        return redirect(url_for("admin_dashboard"))

    return render_template("register.html", registration_open=registration_open)


@auth_bp.route("/auth/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)


@auth_bp.route("/api/auth/profile", methods=["GET", "PATCH"])
@login_required
def profile_api():
    """API для получения и обновления профиля пользователя"""
    if request.method == "GET":
        return jsonify(
            {
                "status": "success",
                "user": {
                    "username": current_user.username,
                    "email": current_user.email,
                    "is_admin": current_user.is_admin,
                    "is_active": current_user.is_active,
                    "id": current_user.id,
                    "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
                },
            }
        )
    
    # PATCH - обновление профиля
    data = request.get_json() or {}
    
    with session_scope() as session:
        # Получаем актуального пользователя из БД
        user = session.get(User, current_user.id)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        # Обновление email
        if "email" in data:
            new_email = (data.get("email") or "").strip() or None
            # Проверка на дубликат email, если указан
            if new_email:
                existing_email = session.query(User).filter(
                    User.email == new_email,
                    User.id != user.id
                ).first()
                if existing_email:
                    return jsonify({"status": "error", "message": f"Email '{new_email}' is already in use"}), 400
            user.email = new_email
        
        # Обновление пароля
        if "new_password" in data and data.get("new_password"):
            # Проверка текущего пароля
            if "current_password" not in data:
                return jsonify({"status": "error", "message": "Current password is required"}), 400
            
            if not verify_password(user.password_hash, data["current_password"]):
                return jsonify({"status": "error", "message": "Current password is incorrect"}), 400
            
            new_password = data["new_password"]
            if len(new_password) < 8:
                return jsonify({"status": "error", "message": "New password must be at least 8 characters long"}), 400
            
            from werkzeug.security import generate_password_hash
            user.password_hash = generate_password_hash(new_password)
        
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
                    "is_admin": user.is_admin,
                    "is_active": user.is_active,
                },
            }
        )


@auth_bp.route("/auth/me")
@login_required
def current_user_info():
    return jsonify(
        {
            "username": current_user.username,
            "email": current_user.email,
            "is_admin": current_user.is_admin,
            "id": current_user.id,
        }
    )

