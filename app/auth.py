import os
from typing import Dict, Any, Optional
from flask import Blueprint, redirect, url_for, session, current_app, Response
from authlib.integrations.flask_client import OAuth
from flask_login import login_user, logout_user, login_required
from .user import User

auth_bp = Blueprint('auth', __name__)
oauth = OAuth()

def init_oauth(app: Any) -> None:
    """
    Initialize Authlib with Google OAuth 2.0 configuration.
    
    Uses OpenID Connect discovery via 'server_metadata_url' for robust
    configuration of endpoints and keys.
    """
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
def login() -> Response:
    """Initiates the Google OAuth 2.0 login flow."""
    redirect_uri = url_for('auth.auth_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@auth_bp.route('/auth/callback')
def auth_callback() -> Any:
    """
    Handles the Google OAuth callback.
    
    Exchanges the authorization code for an access token, parses user info,
    creates the local user session, persists user to DB, and redirects to the main app.
    """
    # Lazy initialization helper for User Service to avoid circular imports
    def get_user_service():
        from .services.user_service import UserService
        return UserService()

    try:
        token = oauth.google.authorize_access_token()
        user_info = _extract_user_info(token)
        
        if not user_info:
            return "Failed to fetch user info", 400

        user = _create_user_from_payload(user_info)
        
        # Persist user to Firestore
        try:
            get_user_service().create_or_update_user(user)
        except Exception as e:
            current_app.logger.error(f"Failed to persist user to Firestore: {e}")
            # We proceed even if persistence fails, as session login works independently
        
        login_user(user)
        
        # Store essential info in session as fallback or for fast access
        session['user_info'] = user.to_dict()
        
        return redirect(url_for('main.index'))
        
    except Exception as e:
        current_app.logger.error(f"OAuth callback failed: {e}", exc_info=True)
        return f"Authentication failed: {e}", 400

@auth_bp.route('/logout')
@login_required
def logout() -> Response:
    """Logs out the current user and clears the session."""
    logout_user()
    session.pop('user_info', None)
    return redirect(url_for('auth.login'))

def _extract_user_info(token: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extracts user information from the OAuth token.
    
    Attempts to get 'userinfo' from the ID token first, falling back to 
    the userinfo endpoint if necessary.
    """
    user_info = token.get('userinfo')
    if not user_info:
        user_info = oauth.google.userinfo()
    return user_info

def _create_user_from_payload(payload: Dict[str, Any]) -> User:
    """
    Creates a User model instance from the OIDC payload.
    
    Handles the mapping of OIDC claims to the User model fields, including 
    the fallback from 'sub' to 'id' for the unique identifier.
    """
    # 'sub' is standard for OIDC, 'id' is used in legacy Google APIs
    user_id = payload.get('sub') or payload.get('id')
    
    return User(
        user_id=str(user_id),
        name=payload.get('name', 'User'),
        email=payload.get('email', ''),
        profile_pic=payload.get('picture', '')
    )
