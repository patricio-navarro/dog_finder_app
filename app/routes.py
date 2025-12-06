import json
import uuid
import logging
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from google.cloud import firestore

# Import the services module to access global variables dynamically
from . import services

main_bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

@main_bp.route('/')
def index():
    return render_template('index.html', maps_api_key=services.GOOGLE_MAPS_API_KEY)

@main_bp.route('/submit', methods=['POST'])
def submit_dog():
    try:
        # 1. Extract Form Data
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        date_str = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        comments = request.form.get('comments', '')
        image_file = request.files.get('image')

        if not lat or not lng or not image_file:
            return jsonify({"error": "Missing required fields"}), 400

        # 2. Upload Image to GCS
        filename = f"{uuid.uuid4()}.jpg"
        image_url = ""
        if services.storage_client:
            try:
                bucket = services.storage_client.bucket(services.BUCKET_NAME)
                blob = bucket.blob(filename)
                blob.upload_from_file(image_file, content_type=image_file.content_type)
                image_url = f"gs://{services.BUCKET_NAME}/{filename}"
                logger.info(f"Uploaded image to {image_url}")
            except Exception as e:
                logger.error(f"Failed to upload to GCS: {e}")
                return jsonify({"error": "Failed to upload image"}), 500
        else:
            logger.info("Skipping GCS upload (client not initialized)")
            image_url = "mock-gcs-url"

        # 3. Reverse Geocoding
        location_details = {
            "latitude": float(lat),
            "longitude": float(lng),
            "city": "",
            "region": "",
            "country": ""
        }

        if services.gmaps:
            try:
                reverse_geocode_result = services.gmaps.reverse_geocode((lat, lng))
                if reverse_geocode_result:
                    # Parse address components
                    for component in reverse_geocode_result[0]['address_components']:
                        if 'locality' in component['types']:
                            location_details['city'] = component['long_name']
                        elif 'administrative_area_level_1' in component['types']:
                            location_details['region'] = component['long_name']
                        elif 'country' in component['types']:
                            location_details['country'] = component['long_name']
            except Exception as e:
                logger.error(f"Geocoding failed: {e}")
        
        # 4. Publish to Pub/Sub
        message_data = {
            "timestamp": datetime.now().isoformat(),
            "sighting_date": date_str,
            "location": location_details,
            "image_url": image_url,
            "user_id": {"string": "mock_user_123"}, # Avro union type requires explicit type wrapper
            "comments": comments
        }
        
        message_json = json.dumps(message_data).encode("utf-8")
        logger.info(f"Publishing message: {message_json.decode('utf-8')}")

        if services.pubsub_publisher:
            try:
                future = services.pubsub_publisher.publish(services.topic_path, message_json)
                message_id = future.result()
                logger.info(f"Published message ID: {message_id}")
            except Exception as e:
                logger.error(f"Failed to publish to Pub/Sub: {e}")
                return jsonify({"error": "Failed to publish data"}), 500
        else:
             logger.info(f"Skipping Pub/Sub publish (client not initialized). Data: {message_data}")

        # 5. Write to Firestore (Hot Storage)
        if services.firestore_client:
            try:
                doc_ref = services.firestore_client.collection("sightings").document()
                doc_ref.set({
                    "timestamp": firestore.SERVER_TIMESTAMP,
                    "sighting_date": date_str,
                    "location": firestore.GeoPoint(float(lat), float(lng)),
                    "location_details": location_details,
                    "image_url": image_url,
                    "comments": comments,
                    "user_id": "mock_user_123", # Mock ID for now
                    "status": "active"
                })
                logger.info(f"Written sighting to Firestore: {doc_ref.id}")
            except Exception as e:
                logger.error(f"Failed to write to Firestore: {e}")
                # We continue even if Firestore fails, as Pub/Sub might have succeeded

        return jsonify({"status": "success", "message": "Dog sighting reported!", "data": message_data}), 200

    except Exception as e:
        logger.exception("An unexpected error occurred")
        return jsonify({"error": str(e)}), 500

@main_bp.route('/api/sightings', methods=['GET'])
def get_sightings():
    if not services.firestore_client:
        return jsonify({"error": "Firestore not available"}), 503
    
    try:
        # Query Parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        cursor = request.args.get('cursor')
        
        # Bounds (north, south, east, west)
        north = request.args.get('north', type=float)
        south = request.args.get('south', type=float)
        east = request.args.get('east', type=float)
        west = request.args.get('west', type=float)
        
        limit = 10 # Desired results per page
        
        # Build Base Query
        # Ordering by sighting_date DESC is crucial for time-based pagination
        query = services.firestore_client.collection("sightings").order_by("sighting_date", direction=firestore.Query.DESCENDING).order_by("timestamp", direction=firestore.Query.DESCENDING)
        
        if start_date:
            query = query.where("sighting_date", ">=", start_date)
        if end_date:
            query = query.where("sighting_date", "<=", end_date)
            
        if cursor:
             cursor_doc_ref = services.firestore_client.collection("sightings").document(cursor)
             cursor_doc = cursor_doc_ref.get()
             if cursor_doc.exists:
                 query = query.start_after(cursor_doc)

        sightings = []
        last_scanned_doc = None
        has_more = False
        
        # "Deep Scan" Loop
        # We process in batches to filter in-memory until we fill the page or run out.
        # This ensures we return 10 matching results even if 50 are out of bounds.
        BATCH_SIZE = 50
        while len(sightings) < limit:
            # Fetch a batch
            current_query = query.limit(BATCH_SIZE)
            docs = list(current_query.stream())
            
            if not docs:
                break # No more data
                
            for doc in docs:
                last_scanned_doc = doc
                data = doc.to_dict()
                
                # GEO FILTER
                include = True
                if north is not None and south is not None and east is not None and west is not None:
                    loc = data.get("location")
                    if loc:
                        lat = loc.latitude
                        lng = loc.longitude
                        # Handle dateline crossing logic if needed, but simple box for now
                        lat_match = south <= lat <= north
                        lng_match = False
                        if west <= east: 
                            lng_match = west <= lng <= east
                        else: # Crosses dateline
                            lng_match = west <= lng or lng <= east
                        
                        if not (lat_match and lng_match):
                            include = False
                    else:
                        include = False # No location, exclude from map search
                
                if include:
                    # Public URL Generation
                    image_url = data.get("image_url", "")
                    signed_url = image_url
                    
                    if image_url and image_url.startswith("gs://"):
                        try:
                            # Use Public URL format: https://storage.googleapis.com/BUCKET/FILE
                            path_parts = image_url.replace("gs://", "").split("/", 1)
                            if len(path_parts) == 2:
                                signed_url = f"https://storage.googleapis.com/{path_parts[0]}/{path_parts[1]}"
                        except Exception as e:
                            logger.error(f"Failed to generate public URL for {image_url}: {e}")
                            pass

                    item = {
                        "id": doc.id,
                        "sighting_date": data.get("sighting_date"),
                        "image_url": signed_url,
                        "location": {
                            "lat": data.get("location").latitude if data.get("location") else 0,
                            "lng": data.get("location").longitude if data.get("location") else 0
                        },
                        "location_details": data.get("location_details"),
                        "comments": data.get("comments", "")
                    }
                    sightings.append(item)
                    
                    if len(sightings) >= limit:
                        has_more = True # We found enough
                        break
            
            # If we finished the batch but didn't find enough matches, 
            # we need to continue the query AFTER the last valid doc we saw from this batch.
            if len(sightings) < limit and docs:
                 query = services.firestore_client.collection("sightings").order_by("sighting_date", direction=firestore.Query.DESCENDING).order_by("timestamp", direction=firestore.Query.DESCENDING)
                 if start_date: query = query.where("sighting_date", ">=", start_date)
                 if end_date: query = query.where("sighting_date", "<=", end_date)
                 query = query.start_after(docs[-1]) # Continue from last fetched doc
            elif not docs:
                 break # exhausted

        next_cursor = None
        if last_scanned_doc:
             next_cursor = last_scanned_doc.id

        return jsonify({
            "data": sightings,
            "next_cursor": next_cursor if has_more or len(sightings) == limit else None # Crude has_more check
        }), 200

    except Exception as e:
        logger.error(f"Failed to fetch sightings: {e}")
        return jsonify({"error": str(e)}), 500
