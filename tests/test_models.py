"""
Tests for sighting data models.
"""
import pytest
from app.models.sighting import Location, SightingSubmission, SightingResponse


class TestLocation:
    """Tests for the Location model."""
    
    def test_location_creation(self):
        """Test creating a Location instance."""
        loc = Location(
            latitude=37.7749,
            longitude=-122.4194,
            city="San Francisco",
            region="California",
            country="USA"
        )
        assert loc.latitude == 37.7749
        assert loc.longitude == -122.4194
        assert loc.city == "San Francisco"
        assert loc.region == "California"
        assert loc.country == "USA"
    
    def test_location_defaults(self):
        """Test Location with default values."""
        loc = Location(latitude=0.0, longitude=0.0)
        assert loc.city == ""
        assert loc.region == ""
        assert loc.country == ""
    
    def test_location_to_dict(self):
        """Test converting Location to dictionary."""
        loc = Location(37.7749, -122.4194, "SF", "CA", "USA")
        result = loc.to_dict()
        assert result == {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "city": "SF",
            "region": "CA",
            "country": "USA"
        }


class TestSightingSubmission:
    """Tests for the SightingSubmission model."""
    
    def test_sighting_submission_creation(self):
        """Test creating a SightingSubmission."""
        sighting = SightingSubmission(
            latitude=37.7749,
            longitude=-122.4194,
            sighting_date="2023-10-27",
            image_url="gs://bucket/image.jpg",
            comments="Nice dog",
            user_id="user123"
        )
        assert sighting.latitude == 37.7749
        assert sighting.longitude == -122.4194
        assert sighting.sighting_date == "2023-10-27"
        assert sighting.image_url == "gs://bucket/image.jpg"
        assert sighting.comments == "Nice dog"
        assert sighting.user_id == "user123"
    
    def test_sighting_submission_defaults(self):
        """Test SightingSubmission with default values."""
        sighting = SightingSubmission(
            latitude=0.0,
            longitude=0.0,
            sighting_date="2023-01-01",
            image_url="test.jpg"
        )
        assert sighting.comments == ""
        assert sighting.user_id is None
    
    def test_to_pubsub_message(self):
        """Test converting to Pub/Sub message format."""
        sighting = SightingSubmission(
            latitude=37.7749,
            longitude=-122.4194,
            sighting_date="2023-10-27",
            image_url="gs://bucket/image.jpg",
            comments="Test",
            user_id="user123"
        )
        msg = sighting.to_pubsub_message()
        
        assert "timestamp" in msg
        assert msg["sighting_date"] == "2023-10-27"
        assert msg["image_url"] == "gs://bucket/image.jpg"
        assert msg["comments"] == "Test"
        assert msg["user_id"] == {"string": "user123"}  # Avro union type
        assert "location" in msg
        assert msg["location"]["latitude"] == 37.7749
        assert msg["location"]["longitude"] == -122.4194
    
    def test_to_pubsub_message_no_user_id(self):
        """Test Pub/Sub message with no user_id defaults to anonymous."""
        sighting = SightingSubmission(
            latitude=0.0,
            longitude=0.0,
            sighting_date="2023-01-01",
            image_url="test.jpg"
        )
        msg = sighting.to_pubsub_message()
        assert msg["user_id"] == {"string": "anonymous"}
    
    def test_to_firestore_document(self):
        """Test converting to Firestore document format."""
        from unittest.mock import MagicMock
        
        sighting = SightingSubmission(
            latitude=37.7749,
            longitude=-122.4194,
            sighting_date="2023-10-27",
            image_url="gs://bucket/image.jpg",
            comments="Test",
            user_id="user123"
        )
        location = Location(37.7749, -122.4194, "SF", "CA", "USA")
        
        doc = sighting.to_firestore_document(location)
        
        assert doc["sighting_date"] == "2023-10-27"
        assert doc["image_url"] == "gs://bucket/image.jpg"
        assert doc["comments"] == "Test"
        assert doc["user_id"] == "user123"
        assert doc["status"] == "active"
        assert "location_details" in doc
        assert doc["location_details"]["city"] == "SF"


class TestSightingResponse:
    """Tests for the SightingResponse model."""
    
    def test_sighting_response_creation(self):
        """Test creating a SightingResponse."""
        response = SightingResponse(
            id="doc123",
            sighting_date="2023-10-27",
            image_url="https://example.com/image.jpg",
            latitude=37.7749,
            longitude=-122.4194,
            location_details={"city": "SF"},
            comments="Test"
        )
        assert response.id == "doc123"
        assert response.sighting_date == "2023-10-27"
        assert response.latitude == 37.7749
    
    def test_from_firestore_doc(self):
        """Test creating from Firestore document."""
        from unittest.mock import MagicMock
        
        mock_geopoint = MagicMock()
        mock_geopoint.latitude = 37.7749
        mock_geopoint.longitude = -122.4194
        
        doc_data = {
            "sighting_date": "2023-10-27",
            "image_url": "gs://bucket/image.jpg",
            "location": mock_geopoint,
            "location_details": {"city": "SF", "region": "CA", "country": "USA"},
            "comments": "Nice dog"
        }
        
        response = SightingResponse.from_firestore_doc("doc123", doc_data)
        
        assert response.id == "doc123"
        assert response.sighting_date == "2023-10-27"
        assert response.latitude == 37.7749
        assert response.longitude == -122.4194
        assert response.comments == "Nice dog"
    
    def test_to_dict(self):
        """Test converting to dictionary for JSON response."""
        response = SightingResponse(
            id="doc123",
            sighting_date="2023-10-27",
            image_url="https://example.com/image.jpg",
            latitude=37.7749,
            longitude=-122.4194,
            location_details={"city": "SF"},
            comments="Test"
        )
        result = response.to_dict()
        
        assert result["id"] == "doc123"
        assert result["sighting_date"] == "2023-10-27"
        assert result["image_url"] == "https://example.com/image.jpg"
        assert result["location"]["lat"] == 37.7749
        assert result["location"]["lng"] == -122.4194
        assert result["location_details"] == {"city": "SF"}
        assert result["comments"] == "Test"
