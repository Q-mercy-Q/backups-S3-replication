from flask_login import LoginManager

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "warning"


def init_auth(app):
    """Register authentication blueprints and init login manager."""
    from .routes import auth_bp  # Local import to avoid circular deps

    login_manager.init_app(app)
    app.register_blueprint(auth_bp)





