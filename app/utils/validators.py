"""
Input validation functions for the Dog Finder application.
"""
import re
from datetime import datetime
from typing import Optional
from werkzeug.datastructures import FileStorage

from ..exceptions import ValidationError


def validate_coordinates(lat: Optional[str], lng: Optional[str]) -> tuple[float, float]:
    """
    Validate and convert latitude/longitude coordinates.
    
    Args:
        lat: Latitude value as string
        lng: Longitude value as string
        
    Returns:
        tuple: (latitude, longitude) as floats
        
    Raises:
        ValidationError: If coordinates are invalid
    """
    if not lat or not lng:
        raise ValidationError("coordinates", "Latitude and longitude are required")
    
    try:
        lat_float = float(lat)
        lng_float = float(lng)
    except (ValueError, TypeError):
        raise ValidationError("coordinates", "Latitude and longitude must be numeric")
    
    if not (-90 <= lat_float <= 90):
        raise ValidationError("latitude", f"Latitude must be between -90 and 90, got {lat_float}")
    
    if not (-180 <= lng_float <= 180):
        raise ValidationError("longitude", f"Longitude must be between -180 and 180, got {lng_float}")
    
    return lat_float, lng_float


def validate_date(date_str: Optional[str]) -> str:
    """
    Validate date string in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        str: Validated date string or today's date if None
        
    Raises:
        ValidationError: If date format is invalid
    """
    if not date_str:
        return datetime.now().strftime('%Y-%m-%d')
    
    # Check format with regex
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        raise ValidationError("date", f"Date must be in YYYY-MM-DD format, got {date_str}")
    
    # Validate it's a real date
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError as e:
        raise ValidationError("date", f"Invalid date: {str(e)}")
    
    return date_str


def validate_image(image_file: Optional[FileStorage], max_size_mb: int = 10) -> FileStorage:
    """
    Validate uploaded image file.
    
    Args:
        image_file: Uploaded file from request
        max_size_mb: Maximum file size in megabytes
        
    Returns:
        FileStorage: Valid image file
        
    Raises:
        ValidationError: If image is invalid
    """
    if not image_file:
        raise ValidationError("image", "Image file is required")
    
    if not image_file.filename:
        raise ValidationError("image", "Image filename is missing")
    
    # Check file extension
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif'}
    file_ext = '.' + image_file.filename.rsplit('.', 1)[-1].lower() if '.' in image_file.filename else ''
    
    if file_ext not in allowed_extensions:
        raise ValidationError("image", f"File type {file_ext} not allowed. Allowed types: {', '.join(allowed_extensions)}")
    
    # Check file size (seek to end to get size, then reset)
    image_file.seek(0, 2)  # Seek to end
    file_size = image_file.tell()
    image_file.seek(0)  # Reset to beginning
    
    max_size_bytes = max_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise ValidationError("image", f"File size ({file_size / 1024 / 1024:.2f}MB) exceeds maximum ({max_size_mb}MB)")
    
    if file_size == 0:
        raise ValidationError("image", "Image file is empty")
    
    return image_file


def validate_bounds(north: Optional[float], south: Optional[float], 
                   east: Optional[float], west: Optional[float]) -> Optional[dict]:
    """
    Validate geographic bounds for filtering.
    
    Args:
        north: Northern latitude boundary
        south: Southern latitude boundary
        east: Eastern longitude boundary
        west: Western longitude boundary
        
    Returns:
        dict: Validated bounds or None if all are None
        
    Raises:
        ValidationError: If bounds are invalid
    """
    # All or none must be provided
    bounds_provided = [b is not None for b in [north, south, east, west]]
    
    if not any(bounds_provided):
        return None
    
    if not all(bounds_provided):
        raise ValidationError("bounds", "All bounds (north, south, east, west) must be provided together")
    
    # Validate latitude bounds
    if not (-90 <= south <= 90):
        raise ValidationError("south", f"South latitude must be between -90 and 90, got {south}")
    
    if not (-90 <= north <= 90):
        raise ValidationError("north", f"North latitude must be between -90 and 90, got {north}")
    
    if south > north:
        raise ValidationError("bounds", f"South latitude ({south}) cannot be greater than north latitude ({north})")
    
    # Validate longitude bounds
    if not (-180 <= west <= 180):
        raise ValidationError("west", f"West longitude must be between -180 and 180, got {west}")
    
    if not (-180 <= east <= 180):
        raise ValidationError("east", f"East longitude must be between -180 and 180, got {east}")
    
    return {
        "north": north,
        "south": south,
        "east": east,
        "west": west
    }


def validate_comments(comments: Optional[str], max_length: int = 1000) -> str:
    """
    Validate comments string.
    
    Args:
        comments: User comments
        max_length: Maximum allowed length
        
    Returns:
        str: Validated comments (empty string if None)
        
    Raises:
        ValidationError: If comments exceed max length
    """
    if not comments:
        return ""
    
    if len(comments) > max_length:
        raise ValidationError("comments", f"Comments exceed maximum length of {max_length} characters")
    
    return comments.strip()
