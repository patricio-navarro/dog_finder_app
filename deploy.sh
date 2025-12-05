#!/bin/bash
set -e

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo ".env file not found!"
    exit 1
fi

# Configuration
# SERVICE_NAME and REGION are loaded from .env
SERVICE_NAME=${SERVICE_NAME:-"dog-finder-app"}
REGION=${REGION:-"us-central1"}
IMAGE_NAME="gcr.io/${GOOGLE_CLOUD_PROJECT}/${SERVICE_NAME}"

echo "=================================================="
echo "Deploying $SERVICE_NAME to $REGION"
echo "Project: $GOOGLE_CLOUD_PROJECT"
echo "=================================================="

# Build and Submit Image to Container Registry (or Artifact Registry)
echo "[1/2] Building and submitting image..."
gcloud builds submit --tag $IMAGE_NAME --project "$GOOGLE_CLOUD_PROJECT" .

# Deploy to Cloud Run
echo "[2/2] Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --project "$GOOGLE_CLOUD_PROJECT" \
    --set-env-vars BUCKET_NAME="$BUCKET_NAME" \
    --set-env-vars TOPIC_ID="$TOPIC_ID" \
    --set-env-vars GOOGLE_MAPS_API_KEY="$GOOGLE_MAPS_API_KEY" \
    --set-env-vars GOOGLE_CLOUD_PROJECT="$GOOGLE_CLOUD_PROJECT"

echo "=================================================="
echo "Deployment Complete!"
echo "=================================================="
