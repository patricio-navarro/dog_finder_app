from typing import Dict, Optional
from flask_login import UserMixin

class User(UserMixin):
    """
    User model for the application.
    
    Since this is a POC without a dedicated users database table, this class 
    acts as a wrapper around user data stored in the session or retrieved 
    from OIDC tokens.
    """
    
    def __init__(self, user_id: str, name: str, email: str, profile_pic: str):
        self.id = user_id
        self.name = name
        self.email = email
        self.profile_pic = profile_pic

    @staticmethod
    def get(user_id: str) -> 'User':
        """
        Static method to retrieve a user.
        
        Note: In a production app with a database, this would query the DB.
        For this POC, we return a partial user object. Full user construction
        happens in the user_loader via session data.
        """
        return User(user_id, "User", user_id, "")
        
    def to_dict(self) -> Dict[str, str]:
        """Returns a dictionary representation of the user."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "profile_pic": self.profile_pic
        }
