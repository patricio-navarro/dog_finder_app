"""
Tests for validation functions.
"""
import pytest
import io
from werkzeug.datastructures import FileStorage
from app.utils.validators import (
    validate_coordinates, validate_date, validate_image,
    validate_bounds, validate_comments
)
from app.exceptions import ValidationError


class TestValidateCoordinates:
    """Tests for coordinate validation."""
    
    def test_valid_coordinates(self):
        """Test valid latitude and longitude."""
        lat, lng = validate_coordinates("37.7749", "-122.4194")
        assert lat == 37.7749
        assert lng == -122.4194
    
    def test_boundary_coordinates(self):
        """Test boundary values."""
        lat, lng = validate_coordinates("90", "180")
        assert lat == 90.0
        assert lng == 180.0
        
        lat, lng = validate_coordinates("-90", "-180")
        assert lat == -90.0
        assert lng == -180.0
    
    def test_missing_latitude(self):
        """Test missing latitude."""
        with pytest.raises(ValidationError) as exc_info:
            validate_coordinates(None, "10")
        assert exc_info.value.field == "coordinates"
    
    def test_missing_longitude(self):
        """Test missing longitude."""
        with pytest.raises(ValidationError) as exc_info:
            validate_coordinates("10", None)
        assert exc_info.value.field == "coordinates"
    
    def test_non_numeric_latitude(self):
        """Test non-numeric latitude."""
        with pytest.raises(ValidationError) as exc_info:
            validate_coordinates("abc", "10")
        assert exc_info.value.field == "coordinates"
        assert "numeric" in exc_info.value.message.lower()
    
    def test_latitude_out_of_range(self):
        """Test latitude out of valid range."""
        with pytest.raises(ValidationError) as exc_info:
            validate_coordinates("91", "10")
        assert exc_info.value.field == "latitude"
        
        with pytest.raises(ValidationError) as exc_info:
            validate_coordinates("-91", "10")
        assert exc_info.value.field == "latitude"
    
    def test_longitude_out_of_range(self):
        """Test longitude out of valid range."""
        with pytest.raises(ValidationError) as exc_info:
            validate_coordinates("10", "181")
        assert exc_info.value.field == "longitude"
        
        with pytest.raises(ValidationError) as exc_info:
            validate_coordinates("10", "-181")
        assert exc_info.value.field == "longitude"


class TestValidateDate:
    """Tests for date validation."""
    
    def test_valid_date(self):
        """Test valid date format."""
        result = validate_date("2023-10-27")
        assert result == "2023-10-27"
    
    def test_none_returns_today(self):
        """Test None returns today's date."""
        result = validate_date(None)
        assert len(result) == 10  # YYYY-MM-DD format
        assert result.count('-') == 2
    
    def test_invalid_format(self):
        """Test invalid date format."""
        with pytest.raises(ValidationError) as exc_info:
            validate_date("10/27/2023")
        assert exc_info.value.field == "date"
        assert "YYYY-MM-DD" in exc_info.value.message
    
    def test_invalid_date_values(self):
        """Test invalid date values."""
        with pytest.raises(ValidationError) as exc_info:
            validate_date("2023-13-01")  # Invalid month
        assert exc_info.value.field == "date"
        
        with pytest.raises(ValidationError) as exc_info:
            validate_date("2023-02-30")  # Invalid day
        assert exc_info.value.field == "date"


class TestValidateImage:
    """Tests for image file validation."""
    
    def test_valid_image(self):
        """Test valid image file."""
        file_data = io.BytesIO(b"fake image data")
        image = FileStorage(file_data, filename="test.jpg", content_type="image/jpeg")
        
        result = validate_image(image)
        assert result == image
    
    def test_missing_image(self):
        """Test missing image file."""
        with pytest.raises(ValidationError) as exc_info:
            validate_image(None)
        assert exc_info.value.field == "image"
        assert "required" in exc_info.value.message.lower()
    
    def test_missing_filename(self):
        """Test image with no filename."""
        file_data = io.BytesIO(b"data")
        image = FileStorage(file_data, filename="")
        
        with pytest.raises(ValidationError) as exc_info:
            validate_image(image)
        assert exc_info.value.field == "image"
    
    def test_invalid_extension(self):
        """Test invalid file extension."""
        file_data = io.BytesIO(b"data")
        image = FileStorage(file_data, filename="test.txt")
        
        with pytest.raises(ValidationError) as exc_info:
            validate_image(image)
        assert exc_info.value.field == "image"
        assert ".txt" in exc_info.value.message
    
    def test_allowed_extensions(self):
        """Test all allowed extensions."""
        for ext in ['jpg', 'jpeg', 'png', 'gif']:
            file_data = io.BytesIO(b"x" * 100)
            image = FileStorage(file_data, filename=f"test.{ext}")
            result = validate_image(image)
            assert result == image
    
    def test_file_too_large(self):
        """Test file size exceeds maximum."""
        # Create 11MB file (exceeds 10MB default)
        file_data = io.BytesIO(b"x" * (11 * 1024 * 1024))
        image = FileStorage(file_data, filename="test.jpg")
        
        with pytest.raises(ValidationError) as exc_info:
            validate_image(image)
        assert exc_info.value.field == "image"
        assert "size" in exc_info.value.message.lower()
    
    def test_empty_file(self):
        """Test empty file."""
        file_data = io.BytesIO(b"")
        image = FileStorage(file_data, filename="test.jpg")
        
        with pytest.raises(ValidationError) as exc_info:
            validate_image(image)
        assert exc_info.value.field == "image"
        assert "empty" in exc_info.value.message.lower()


class TestValidateBounds:
    """Tests for geographic bounds validation."""
    
    def test_valid_bounds(self):
        """Test valid bounds."""
        result = validate_bounds(40.0, 30.0, -120.0, -130.0)
        assert result == {
            "north": 40.0,
            "south": 30.0,
            "east": -120.0,
            "west": -130.0
        }
    
    def test_all_none_returns_none(self):
        """Test all None returns None."""
        result = validate_bounds(None, None, None, None)
        assert result is None
    
    def test_partial_bounds_raises_error(self):
        """Test providing only some bounds raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_bounds(40.0, 30.0, None, None)
        assert exc_info.value.field == "bounds"
        assert "together" in exc_info.value.message.lower()
    
    def test_invalid_latitude_bounds(self):
        """Test invalid latitude values."""
        with pytest.raises(ValidationError) as exc_info:
            validate_bounds(40.0, 91.0, 10.0, 0.0)  # South > 90
        assert exc_info.value.field == "south"
        
        with pytest.raises(ValidationError) as exc_info:
            validate_bounds(91.0, 30.0, 10.0, 0.0)  # North > 90
        assert exc_info.value.field == "north"
    
    def test_south_greater_than_north(self):
        """Test south > north raises error."""
        with pytest.raises(ValidationError) as exc_info:
            validate_bounds(30.0, 40.0, 10.0, 0.0)  # South > North
        assert exc_info.value.field == "bounds"
    
    def test_invalid_longitude_bounds(self):
        """Test invalid longitude values."""
        with pytest.raises(ValidationError) as exc_info:
            validate_bounds(40.0, 30.0, 10.0, -181.0)  # West < -180
        assert exc_info.value.field == "west"
        
        with pytest.raises(ValidationError) as exc_info:
            validate_bounds(40.0, 30.0, 181.0, 0.0)  # East > 180
        assert exc_info.value.field == "east"


class TestValidateComments:
    """Tests for comments validation."""
    
    def test_valid_comments(self):
        """Test valid comments string."""
        result = validate_comments("This is a test comment")
        assert result == "This is a test comment"
    
    def test_none_returns_empty_string(self):
        """Test None returns empty string."""
        result = validate_comments(None)
        assert result == ""
    
    def test_empty_string_returns_empty(self):
        """Test empty string returns empty."""
        result = validate_comments("")
        assert result == ""
    
    def test_strips_whitespace(self):
        """Test whitespace is stripped."""
        result = validate_comments("  test  ")
        assert result == "test"
    
    def test_exceeds_max_length(self):
        """Test comments exceeding max length."""
        long_comment = "x" * 1001
        with pytest.raises(ValidationError) as exc_info:
            validate_comments(long_comment)
        assert exc_info.value.field == "comments"
        assert "1000" in exc_info.value.message
    
    def test_custom_max_length(self):
        """Test custom max length."""
        result = validate_comments("test", max_length=10)
        assert result == "test"
        
        with pytest.raises(ValidationError):
            validate_comments("this is too long", max_length=10)
