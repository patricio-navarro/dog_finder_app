from datetime import datetime
from typing import Dict, Optional, Any
from flask_login import UserMixin

class User(UserMixin):
    """
    User model for the application with Firestore support.
    """
    
    def __init__(self, user_id: str, name: str, email: str, profile_pic: str, 
                 created_at: Optional[datetime] = None, last_login: Optional[datetime] = None):
        self.id = user_id
        self.name = name
        self.email = email
        self.profile_pic = profile_pic
        self.created_at = created_at or datetime.utcnow()
        self.last_login = last_login or datetime.utcnow()

    @staticmethod
    def get(user_id: str) -> 'User':
        """
        Static method to retrieve a user.
        Deprecated: Use UserService.get_user instead.
        """
        return User(user_id, "User", user_id, "")
        
    def to_dict(self) -> Dict[str, str]:
        """Returns a dictionary representation of the user (session safe)."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "profile_pic": self.profile_pic,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "last_login": self.last_login.isoformat() if self.last_login else ""
        }

    def to_firestore_dict(self) -> Dict[str, Any]:
        """Returns a dictionary for Firestore storage."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "profile_pic": self.profile_pic,
            "created_at": self.created_at,
            "last_login": self.last_login
        }

    @classmethod
    def from_firestore(cls, data: Dict[str, Any]) -> 'User':
        """Creates a User instance from Firestore data."""
        return cls(
            user_id=data.get('id', ''),
            name=data.get('name', ''),
            email=data.get('email', ''),
            profile_pic=data.get('profile_pic', ''),
            created_at=data.get('created_at'),
            last_login=data.get('last_login')
        )
