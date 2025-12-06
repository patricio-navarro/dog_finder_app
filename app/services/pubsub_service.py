"""
Pub/Sub service for publishing sighting messages.
"""
import json
import logging
from typing import Optional

from ..exceptions import PublishError, ServiceUnavailableError
from .. import gcp_clients

logger = logging.getLogger(__name__)


class PubSubService:
    """Service for publishing messages to Google Cloud Pub/Sub."""
    
    def __init__(self, publisher=None, topic_path: str = ""):
        """
        Initialize Pub/Sub service.
        
        Args:
            publisher: Pub/Sub publisher client (or None to use global client)
            topic_path: Full topic path
        """
        self.publisher = publisher or gcp_clients.pubsub_publisher
        self.topic_path = topic_path or gcp_clients.topic_path
    
    def publish_sighting(self, message_data: dict) -> Optional[str]:
        """
        Publish sighting message to Pub/Sub.
        
        Args:
            message_data: Dictionary containing sighting data (must match Avro schema)
            
        Returns:
            str: Message ID if published successfully, None if client not initialized
            
        Raises:
            ServiceUnavailableError: If publisher client is not initialized
            PublishError: If publishing fails
        """
        if not self.publisher:
            logger.info(f"Skipping Pub/Sub publish (client not initialized). Data: {message_data}")
            return None
        
        try:
            # Ensure Avro union type formatting for user_id
            if 'user_id' in message_data and not isinstance(message_data['user_id'], dict):
                message_data['user_id'] = {"string": message_data['user_id']}
            
            message_json = json.dumps(message_data).encode("utf-8")
            logger.info(f"Publishing message: {message_json.decode('utf-8')}")
            
            future = self.publisher.publish(self.topic_path, message_json)
            message_id = future.result(timeout=30)
            
            logger.info(f"Published message ID: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Failed to publish to Pub/Sub: {e}")
            raise PublishError(f"Failed to publish message: {str(e)}")
    
    def format_avro_message(self, sighting_data: dict) -> dict:
        """
        Format message data with Avro union type handling.
        
        Args:
            sighting_data: Raw sighting data
            
        Returns:
            dict: Message data formatted for Pub/Sub with Avro schema compliance
        """
        # Ensure user_id uses Avro union type format
        formatted = sighting_data.copy()
        
        if 'user_id' in formatted:
            user_id = formatted['user_id']
            if user_id and not isinstance(user_id, dict):
                formatted['user_id'] = {"string": user_id}
            elif not user_id:
                formatted['user_id'] = {"string": "anonymous"}
        
        return formatted
