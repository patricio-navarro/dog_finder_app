"""
Data models and schemas for the Dog Finder application.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Location:
    """Location information for a dog sighting."""
    latitude: float
    longitude: float
    city: str = ""
    region: str = ""
    country: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "city": self.city,
            "region": self.region,
            "country": self.country
        }


@dataclass
class SightingSubmission:
    """Represents a dog sighting submission from the form."""
    latitude: float
    longitude: float
    sighting_date: str
    image_url: str
    comments: str = ""
    user_id: Optional[str] = None
    
    def to_pubsub_message(self) -> dict:
        """
        Convert to Pub/Sub message format with Avro union type handling.
        
        Returns:
            dict: Message data formatted for Pub/Sub with Avro schema
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "sighting_date": self.sighting_date,
            "location": {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "city": "",  # Will be populated by geocoding service
                "region": "",
                "country": ""
            },
            "image_url": self.image_url,
            "user_id": {"string": self.user_id} if self.user_id else {"string": "anonymous"},  # Avro union type
            "comments": self.comments
        }
    
    def to_firestore_document(self, location: Location) -> dict:
        """
        Convert to Firestore document format.
        
        Args:
            location: Location object with geocoded information
            
        Returns:
            dict: Document data for Firestore
        """
        from google.cloud import firestore as firestore_module
        
        return {
            "timestamp": firestore_module.SERVER_TIMESTAMP,
            "sighting_date": self.sighting_date,
            "location": firestore_module.GeoPoint(self.latitude, self.longitude),
            "location_details": location.to_dict(),
            "image_url": self.image_url,
            "comments": self.comments,
            "user_id": self.user_id or "anonymous",
            "status": "active"
        }


@dataclass
class SightingResponse:
    """Represents a sighting in API responses."""
    id: str
    sighting_date: str
    image_url: str
    latitude: float
    longitude: float
    location_details: dict
    comments: str
    
    @classmethod
    def from_firestore_doc(cls, doc_id: str, data: dict) -> 'SightingResponse':
        """Create from Firestore document."""
        location = data.get("location")
        return cls(
            id=doc_id,
            sighting_date=data.get("sighting_date", ""),
            image_url=data.get("image_url", ""),
            latitude=location.latitude if location else 0,
            longitude=location.longitude if location else 0,
            location_details=data.get("location_details", {}),
            comments=data.get("comments", "")
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON response."""
        return {
            "id": self.id,
            "sighting_date": self.sighting_date,
            "image_url": self.image_url,
            "location": {
                "lat": self.latitude,
                "lng": self.longitude
            },
            "location_details": self.location_details,
            "comments": self.comments
        }
