import logging
from typing import Tuple
from flask import Blueprint, render_template, request, jsonify, Response
from flask_wtf.csrf import generate_csrf
from flask_login import login_required, current_user

from . import gcp_clients, limiter, csrf
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
from .config import DEFAULT_PAGE_LIMIT

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)


def get_storage_service() -> StorageService:
    """Get storage service instance with initialized clients."""
    return StorageService()


def get_geocoding_service() -> GeocodingService:
    """Get geocoding service instance with initialized clients."""
    return GeocodingService()


def get_pubsub_service() -> PubSubService:
    """Get Pub/Sub service instance with initialized clients."""
    return PubSubService()


def get_sighting_service() -> SightingService:
    """Get sighting service instance with initialized clients."""
    return SightingService()


@main_bp.route('/')
@login_required
def index() -> str:
    """Render main page."""
    csrf_token = generate_csrf()
    return render_template(
        'index.html',
        maps_api_key=gcp_clients.GOOGLE_MAPS_API_KEY,
        csrf_token=csrf_token,
        user=current_user
    )


@main_bp.route('/submit', methods=['POST'])
@login_required
@limiter.limit("20 per hour")
def submit_dog() -> Tuple[Response, int]:
    """
    Submit a dog sighting.
    
    Validates input, uploads image, geocodes location, publishes to Pub/Sub,
    and stores in Firestore.
    """
    try:
        latitude, longitude = validate_coordinates(
            request.form.get('lat'),
            request.form.get('lng')
        )
        formatted_date = validate_date(request.form.get('date'))
        sanitized_comments = validate_comments(request.form.get('comments', ''))
        uploaded_image_file = validate_image(request.files.get('image'))
        
        image_url = get_storage_service().upload_image(uploaded_image_file)
        location_data = get_geocoding_service().reverse_geocode(latitude, longitude)
        
        sighting_submission = SightingSubmission(
            latitude=latitude,
            longitude=longitude,
            sighting_date=formatted_date,
            image_url=image_url,
            comments=sanitized_comments,
            user_id=current_user.id
        )
        
        pubsub_payload = sighting_submission.to_pubsub_message()
        pubsub_payload['location'] = location_data.to_dict()
        
        try:
            get_pubsub_service().publish_sighting(pubsub_payload)
        except Exception as pubsub_err:
            logger.error(f"Failed to publish to Pub/Sub: {pubsub_err}")
        
        firestore_document = sighting_submission.to_firestore_document(location_data)
        try:
            document_id = get_sighting_service().create_sighting(firestore_document)
            logger.info(f"Created sighting: {document_id}")
        except Exception as firestore_err:
            logger.error(f"Failed to write to Firestore: {firestore_err}")
        
        return jsonify({
            "status": "success",
            "message": "Dog sighting reported!",
            "data": pubsub_payload
        }), 200
    
    except ValidationError as validation_err:
        return jsonify({"error": f"{validation_err.field}: {validation_err.message}"}), 400
    
    except ServiceUnavailableError as service_err:
        return jsonify({"error": str(service_err)}), 503
    
    except Exception:
        logger.exception("Unexpected error during sighting submission")
        return jsonify({"error": "An unexpected error occurred"}), 500


@main_bp.route('/api/sightings', methods=['GET'])
@csrf.exempt
@login_required
def get_sightings() -> Tuple[Response, int]:
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
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        pagination_cursor = request.args.get('cursor')
        page_limit = request.args.get('limit', type=int, default=DEFAULT_PAGE_LIMIT)
        
        geographic_bounds = validate_bounds(
            request.args.get('north', type=float),
            request.args.get('south', type=float),
            request.args.get('east', type=float),
            request.args.get('west', type=float)
        )
        
        search_filters = {}
        if start_date:
            search_filters['start_date'] = start_date
        if end_date:
            search_filters['end_date'] = end_date
        if geographic_bounds:
            search_filters['bounds'] = geographic_bounds
        
        sightings_result = get_sighting_service().get_sightings(search_filters, pagination_cursor, page_limit)
        
        for sighting_record in sightings_result['data']:
            if sighting_record.get('image_url'):
                sighting_record['image_url'] = gs_to_public_url(sighting_record['image_url'])
        
        return jsonify(sightings_result), 200
    
    except ValidationError as validation_err:
        return jsonify({"error": f"{validation_err.field}: {validation_err.message}"}), 400
    
    except ServiceUnavailableError as service_err:
        return jsonify({"error": str(service_err)}), 503
    
    except Exception:
        logger.exception("Unexpected error during sightings retrieval")
        return jsonify({"error": "An unexpected error occurred"}), 500
