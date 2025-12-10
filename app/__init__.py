import os
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from .gcp_clients import init_services


# Initialize extensions
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    
    # Secret key for CSRF (use environment variable in production)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # CSRF settings
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour token validity
    
    # Initialize extensions
    limiter.init_app(app)
    csrf.init_app(app)
    
    # Initialize Global Services
    init_services()
    
    # Register Blueprints
    from .routes import main_bp
    app.register_blueprint(main_bp)
    
    return app

