import os
import uuid
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from google.cloud import storage
from google.cloud import pubsub_v1
import googlemaps
from dotenv import load_dotenv

# Load environment variables for local testing
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BUCKET_NAME = os.getenv("BUCKET_NAME", "analytics-presentation-poc-lost-dogs")
TOPIC_ID = os.getenv("TOPIC_ID", "dog-found-topic")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "YOUR_GOOGLE_MAPS_API_KEY")

# Initialize Clients
# Note: In Cloud Run, these will use the service account attached to the service.
# Locally, you need GOOGLE_APPLICATION_CREDENTIALS set.
try:
    storage_client = storage.Client()
    pubsub_publisher = pubsub_v1.PublisherClient()
    topic_path = pubsub_publisher.topic_path(PROJECT_ID, TOPIC_ID)
except Exception as e:
    logger.warning(f"Could not initialize GCP clients (expected during build/test without creds): {e}")
    storage_client = None
    pubsub_publisher = None

try:
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
except Exception as e:
    logger.warning(f"Could not initialize Google Maps client: {e}")
    gmaps = None

@app.route('/')
def index():
    return render_template('index.html', maps_api_key=GOOGLE_MAPS_API_KEY)

@app.route('/submit', methods=['POST'])
def submit_dog():
    try:
        # 1. Extract Form Data
        lat = request.form.get('lat')
        lng = request.form.get('lng')
        date_str = request.form.get('date', datetime.now().strftime('%Y-%m-%d'))
        image_file = request.files.get('image')

        if not lat or not lng or not image_file:
            return jsonify({"error": "Missing required fields"}), 400

        # 2. Upload Image to GCS
        filename = f"{uuid.uuid4()}.jpg"
        image_url = ""
        if storage_client:
            try:
                bucket = storage_client.bucket(BUCKET_NAME)
                blob = bucket.blob(filename)
                blob.upload_from_file(image_file, content_type=image_file.content_type)
                image_url = f"gs://{BUCKET_NAME}/{filename}"
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

        if gmaps:
            try:
                reverse_geocode_result = gmaps.reverse_geocode((lat, lng))
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
            "image_url": image_url
        }
        
        message_json = json.dumps(message_data).encode("utf-8")
        logger.info(f"Publishing message: {message_json.decode('utf-8')}")

        if pubsub_publisher:
            try:
                future = pubsub_publisher.publish(topic_path, message_json)
                message_id = future.result()
                logger.info(f"Published message ID: {message_id}")
            except Exception as e:
                logger.error(f"Failed to publish to Pub/Sub: {e}")
                return jsonify({"error": "Failed to publish data"}), 500
        else:
             logger.info(f"Skipping Pub/Sub publish (client not initialized). Data: {message_data}")

        return jsonify({"status": "success", "message": "Dog sighting reported!", "data": message_data}), 200

    except Exception as e:
        logger.exception("An unexpected error occurred")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8080)
