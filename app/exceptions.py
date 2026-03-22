"""
Custom exception classes for the Dog Finder application.
"""


class DogFinderError(Exception):
    """Base exception for all Dog Finder errors."""
    pass


class ValidationError(DogFinderError):
    """Raised when input validation fails."""
    
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class StorageError(DogFinderError):
    """Raised when GCS operations fail."""
    pass


class ServiceUnavailableError(DogFinderError):
    """Raised when required service clients are not initialized."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"{service_name} service is not available")


class GeocodingError(DogFinderError):
    """Raised when geocoding operations fail."""
    pass


class PublishError(DogFinderError):
    """Raised when publishing to Pub/Sub fails."""
    pass
