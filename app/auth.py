import os
from flask import Blueprint, redirect, url_for, session, current_app
from authlib.integrations.flask_client import OAuth
from flask_login import login_user, logout_user, login_required
from .user import User

auth_bp = Blueprint('auth', __name__)
oauth = OAuth()

def init_oauth(app):
    """Initialize Authlib with Google configuration."""
    oauth.init_app(app)
    oauth.register(
        name='google',
        client_id=os.getenv('GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )

@auth_bp.route('/login')
def login():
    """Initiate Google Login."""
    # Build absolute URL for callback
    redirect_uri = url_for('auth.auth_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/auth/callback')
def auth_callback():
    """Handle Google OAuth callback."""
    try:
        token = oauth.google.authorize_access_token()
        # Parse ID token
        user_info = token.get('userinfo')
        if not user_info:
            # Fallback if userinfo not in token (depends on scopes)
            user_info = oauth.google.userinfo()
            
        if not user_info:
            return "Failed to fetch user info", 400

        # Create user object
        # OIDC uses 'sub', legacy Google APIs use 'id'
        user_id = user_info.get('sub') or user_info.get('id')
        name = user_info.get('name', 'User')
        email = user_info.get('email', '')
        picture = user_info.get('picture', '')
        
        user = User(user_id=user_id, name=name, email=email, profile_pic=picture)
        
        # Log in (Flask-Login)
        login_user(user)
        
        # Store essential info in session for reconstruction
        session['user_info'] = user.to_dict()
        
        return redirect(url_for('main.index'))
        
    except Exception as e:
        current_app.logger.error(f"OAuth failed: {e}")
        return f"Authentication failed: {e}", 400

@auth_bp.route('/logout')
@login_required
def logout():
    """Log out user."""
    logout_user()
    session.pop('user_info', None)
    return redirect(url_for('auth.login')) # Or index, but index is protected now
