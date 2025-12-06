"""
Configuration constants for the Dog Finder application.
"""

# Pagination
DEFAULT_PAGE_LIMIT = 10
BATCH_SIZE = 50

# Image upload
MAX_IMAGE_SIZE_MB = 10
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif'}

# Validation
MAX_COMMENTS_LENGTH = 1000

# Firestore
SIGHTINGS_COLLECTION = "sightings"

# Default values
DEFAULT_USER_ID = "anonymous"
MOCK_USER_ID = "mock_user_123"
