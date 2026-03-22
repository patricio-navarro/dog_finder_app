import os
from typing import Optional

from flask import Flask, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

from .gcp_clients import init_services


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'


def create_app() -> Flask:
    """Initialize and configure the Flask application."""
    app = Flask(__name__)
    
    secret_key = os.getenv('FLASK_SECRET_KEY')
    if not secret_key:
        raise EnvironmentError("FLASK_SECRET_KEY environment variable is strictly required.")
    
    app.config['SECRET_KEY'] = secret_key
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600
    
    limiter.init_app(app)
    csrf.init_app(app)
    login_manager.init_app(app)
    
    from .auth import init_oauth, auth_bp, configure_login_manager
    init_oauth(app)
    configure_login_manager(login_manager)
    app.register_blueprint(auth_bp)

    init_services()
    
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    return app
