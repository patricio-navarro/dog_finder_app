"""
Tests for custom exception classes.
"""
import pytest
from app.exceptions import (
    DogFinderError, ValidationError, StorageError,
    ServiceUnavailableError, GeocodingError, PublishError
)


def test_base_exception():
    """Test base DogFinderError exception."""
    error = DogFinderError("Test error")
    assert str(error) == "Test error"
    assert isinstance(error, Exception)


def test_validation_error():
    """Test ValidationError with field and message."""
    error = ValidationError("email", "Invalid email format")
    assert error.field == "email"
    assert error.message == "Invalid email format"
    assert str(error) == "email: Invalid email format"
    assert isinstance(error, DogFinderError)


def test_storage_error():
    """Test StorageError exception."""
    error = StorageError("Failed to upload file")
    assert str(error) == "Failed to upload file"
    assert isinstance(error, DogFinderError)


def test_service_unavailable_error():
    """Test ServiceUnavailableError with service name."""
    error = ServiceUnavailableError("Firestore")
    assert error.service_name == "Firestore"
    assert str(error) == "Firestore service is not available"
    assert isinstance(error, DogFinderError)


def test_geocoding_error():
    """Test GeocodingError exception."""
    error = GeocodingError("API timeout")
    assert str(error) == "API timeout"
    assert isinstance(error, DogFinderError)


def test_publish_error():
    """Test PublishError exception."""
    error = PublishError("Pub/Sub publish failed")
    assert str(error) == "Pub/Sub publish failed"
    assert isinstance(error, DogFinderError)
