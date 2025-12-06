import os
import logging
from google.cloud import storage
from google.cloud import pubsub_v1
from google.cloud import firestore
import googlemaps
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BUCKET_NAME = os.getenv("BUCKET_NAME", "analytics-presentation-poc-lost-dogs")
TOPIC_ID = os.getenv("TOPIC_ID", "dog-found-topic")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "YOUR_GOOGLE_MAPS_API_KEY")

# Initialize Clients
storage_client = None
pubsub_publisher = None
topic_path = None
firestore_client = None
gmaps = None

def init_services():
    global storage_client, pubsub_publisher, topic_path, firestore_client, gmaps
    
    logger.info("Initializing services...")
    
    # Storage & PubSub
    try:
        storage_client = storage.Client()
        pubsub_publisher = pubsub_v1.PublisherClient()
        topic_path = pubsub_publisher.topic_path(PROJECT_ID, TOPIC_ID)
        logger.info(f"Successfully initialized Storage and Pub/Sub clients. Topic: {topic_path}")
    except Exception as e:
        logger.error(f"Failed to initialize GCP clients: {e}")

    # Firestore
    try:
        firestore_client = firestore.Client()
        logger.info("Successfully initialized Firestore client")
    except Exception as e:
        logger.error(f"Failed to initialize Firestore client: {e}")

    # Maps
    try:
        gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        logger.info("Successfully initialized Google Maps client")
    except Exception as e:
        logger.error(f"Failed to initialize Google Maps client: {e}")
