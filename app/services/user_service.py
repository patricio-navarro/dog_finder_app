"""
Service layer for user management and retrieval.
"""
import logging
from typing import Optional, Any

from ..user import User
from ..exceptions import ServiceUnavailableError
from .. import gcp_clients

logger = logging.getLogger(__name__)


class UserService:
    """Service handling user-related operations."""
    
    def __init__(self, firestore_client: Optional[Any] = None):
        """
        Initialize user service.
        
        Args:
            firestore_client: Firestore client (or None to use global client)
        """
        self.firestore = firestore_client or gcp_clients.firestore_client
        self.collection_name = "users"
    
    def get_user(self, user_id: str) -> Optional[User]:
        """
        Retrieve a user by ID from Firestore.
        
        Args:
            user_id: The unique user ID
            
        Returns:
            User object if found, None otherwise
            
        Raises:
            ServiceUnavailableError: If Firestore client is not initialized
        """
        if not self.firestore:
            raise ServiceUnavailableError("Firestore")
            
        try:
            doc_ref = self.firestore.collection(self.collection_name).document(user_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return User.from_firestore(doc.to_dict())
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve user {user_id}: {e}")
            return None

    def create_or_update_user(self, user: User) -> bool:
        """
        Create or update a user in Firestore.
        
        Args:
            user: User object to persist
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ServiceUnavailableError: If Firestore client is not initialized
        """
        if not self.firestore:
            raise ServiceUnavailableError("Firestore")
            
        try:
            doc_ref = self.firestore.collection(self.collection_name).document(user.id)
            
            # Merge=True ensures we update existing fields or create if new
            # We want to preserve 'created_at' if it exists, but the model handles that logic,
            # or we can use set(..., merge=True).
            # Using merge=True is safer.
            user_data = user.to_firestore_dict()
            doc_ref.set(user_data, merge=True)
            
            logger.info(f"Persisted user: {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to persist user {user.id}: {e}")
            return False
