from flask import Flask
from .gcp_clients import init_services
from .routes import main_bp

def create_app():
    app = Flask(__name__)
    
    # Initialize Global Services
    init_services()
    
    # Register Blueprints
    app.register_blueprint(main_bp)
    
    return app
