"""
Refactored route handlers using service layer pattern.

This module provides thin HTTP handlers that delegate to service classes.
Business logic, validation, and data access are handled by dedicated services.
"""
import logging
from flask import Blueprint, render_template, request, jsonify

from . import gcp_clients
from .services.storage_service import StorageService
from .services.geocoding_service import GeocodingService
from .services.pubsub_service import PubSubService
from .services.sighting_service import SightingService
from .models.sighting import SightingSubmission
from .utils.validators import (
    validate_coordinates, validate_date, validate_image,
    validate_bounds, validate_comments
)
from .utils.url_helpers import gs_to_public_url
from .exceptions import ValidationError, ServiceUnavailableError
from .config import DEFAULT_PAGE_LIMIT, MOCK_USER_ID

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)


# Lazy initialization helpers - services are created when first accessed
def get_storage_service():
    """Get storage service instance with initialized clients."""
    return StorageService()


def get_geocoding_service():
    """Get geocoding service instance with initialized clients."""
    return GeocodingService()


def get_pubsub_service():
    """Get Pub/Sub service instance with initialized clients."""
    return PubSubService()


def get_sighting_service():
    """Get sighting service instance with initialized clients."""
    return SightingService()



@main_bp.route('/')
def index():
    """Render main page."""
    return render_template('index.html', maps_api_key=gcp_clients.GOOGLE_MAPS_API_KEY)


@main_bp.route('/submit', methods=['POST'])
def submit_dog():
    """
    Submit a dog sighting.
    
    Validates input, uploads image, geocodes location, publishes to Pub/Sub,
    and stores in Firestore.
    """
    try:
        # 1. Validate and extract form data
        lat, lng = validate_coordinates(
            request.form.get('lat'),
            request.form.get('lng')
        )
        date_str = validate_date(request.form.get('date'))
        comments = validate_comments(request.form.get('comments', ''))
        image_file = validate_image(request.files.get('image'))
        
        # 2. Upload image to GCS
        image_url = get_storage_service().upload_image(image_file)
        
        # 3. Reverse geocode coordinates
        location = get_geocoding_service().reverse_geocode(lat, lng)
        
        # 4. Create sighting submission model
        sighting = SightingSubmission(
            latitude=lat,
            longitude=lng,
            sighting_date=date_str,
            image_url=image_url,
            comments=comments,
            user_id=MOCK_USER_ID  # TODO: Replace with actual user ID from auth
        )
        
        # 5. Publish to Pub/Sub
        pubsub_message = sighting.to_pubsub_message()
        # Update location in message with geocoded details
        pubsub_message['location'] = location.to_dict()
        
        try:
            get_pubsub_service().publish_sighting(pubsub_message)
        except Exception as e:
            # Log error but don't fail the request
            logger.error(f"Failed to publish to Pub/Sub: {e}")
        
        # 6. Write to Firestore
        firestore_doc = sighting.to_firestore_document(location)
        try:
            doc_id = get_sighting_service().create_sighting(firestore_doc)
            logger.info(f"Created sighting: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to write to Firestore: {e}")
            # Continue even if Firestore fails (Pub/Sub might have succeeded)
        
        return jsonify({
            "status": "success",
            "message": "Dog sighting reported!",
            "data": pubsub_message
        }), 200
    
    except ValidationError as e:
        return jsonify({"error": f"{e.field}: {e.message}"}), 400
    
    except ServiceUnavailableError as e:
        return jsonify({"error": str(e)}), 503
    
    except Exception as e:
        logger.exception("Unexpected error during sighting submission")
        return jsonify({"error": "An unexpected error occurred"}), 500


@main_bp.route('/api/sightings', methods=['GET'])
def get_sightings():
    """
    Get dog sightings with optional filtering and pagination.
    
    Query parameters:
        - start_date: Start date filter (YYYY-MM-DD)
        - end_date: End date filter (YYYY-MM-DD)
        - north, south, east, west: Geographic bounds
        - cursor: Pagination cursor (document ID)
        - limit: Results per page (default: 10)
    """
    try:
        # Validate query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        cursor = request.args.get('cursor')
        limit = request.args.get('limit', type=int, default=DEFAULT_PAGE_LIMIT)
        
        # Validate bounds if provided
        bounds = validate_bounds(
            request.args.get('north', type=float),
            request.args.get('south', type=float),
            request.args.get('east', type=float),
            request.args.get('west', type=float)
        )
        
        # Build filters
        filters = {}
        if start_date:
            filters['start_date'] = start_date
        if end_date:
            filters['end_date'] = end_date
        if bounds:
            filters['bounds'] = bounds
        
        # Query sightings
        result = get_sighting_service().get_sightings(filters, cursor, limit)
        
        # Convert GCS URLs to public URLs
        for sighting in result['data']:
            if sighting.get('image_url'):
                sighting['image_url'] = gs_to_public_url(sighting['image_url'])
        
        return jsonify(result), 200
    
    except ValidationError as e:
        return jsonify({"error": f"{e.field}: {e.message}"}), 400
    
    except ServiceUnavailableError as e:
        return jsonify({"error": str(e)}), 503
    
    except Exception as e:
        logger.exception("Unexpected error during sightings retrieval")
        return jsonify({"error": "An unexpected error occurred"}), 500
