import os
from typing import Optional
from flask import Flask, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from .gcp_clients import init_services


# Initialize extensions
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Redirect here if not logged in

def create_app() -> Flask:
    """Initialize and configure the Flask application."""
    app = Flask(__name__)
    
    # Secret key for CSRF and Session (use environment variable in production)
    secret_key = os.getenv('FLASK_SECRET_KEY')
    if not secret_key:
        secret_key = 'dev-secret-key-change-in-production'
    app.config['SECRET_KEY'] = secret_key
    
    # CSRF settings
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour token validity
    
    # Initialize extensions
    limiter.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    
    # Initialize OAuth
    from .auth import init_oauth, auth_bp
    init_oauth(app)
    app.register_blueprint(auth_bp)

    # User Loader
    from .user import User
    @login_manager.user_loader
    def load_user(user_id: str) -> Optional[User]:
        """
        Load user from session data.
        
        Since we don't have a database, we reconstruct the User object
        from the session info stored during login.
        """
        user_info = session.get('user_info')
        if user_info and user_info.get('id') == user_id:
            return User(
                user_id=user_info['id'],
                name=user_info['name'],
                email=user_info['email'],
                profile_pic=user_info['profile_pic']
            )
        return None
    
    # Initialize Global Services
    init_services()
    
    # Register Blueprints
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    # Fix for Cloud Run / Load Balancer (HTTPS)
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    return app

