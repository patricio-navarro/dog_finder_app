#!/bin/bash

# Load environment variables
# Determine script location and project root
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$DIR/.."

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    source "$PROJECT_ROOT/.env"
else
    echo "❌ .env file not found!"
    exit 1
fi

# Check required variables
if [ -z "$GOOGLE_CLOUD_PROJECT" ] || [ -z "$BUCKET_NAME" ] || [ -z "$TOPIC_ID" ] || [ -z "$REGION" ] || [ -z "$BIGQUERY_DATASET" ] || [ -z "$BIGQUERY_TABLE" ] || [ -z "$SERVICE_NAME" ]; then
    echo "❌ Missing required environment variables in .env"
    exit 1
fi

SCHEMA_ID="${TOPIC_ID}-schema"
SUBSCRIPTION_ID="${TOPIC_ID}-bq-sub"

echo "=================================================="
echo "🗑️  Cleaning up Cloud Resources"
echo "Project: $GOOGLE_CLOUD_PROJECT"
echo "=================================================="
echo "⚠️  WARNING: This will DELETE all resources listed below:"
echo "   - Cloud Run Service: $SERVICE_NAME"
echo "   - Subscription:      $SUBSCRIPTION_ID"
echo "   - Topic:             $TOPIC_ID"
echo "   - Schema:            $SCHEMA_ID"
echo "   - BigQuery Table:    $BIGQUERY_TABLE"
echo "   - BigQuery Dataset:  $BIGQUERY_DATASET"
echo "   - GCS Bucket:        $BUCKET_NAME"
echo "=================================================="
read -p "Are you sure you want to proceed? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "[1/7] Deleting Cloud Run Service..."
if gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$GOOGLE_CLOUD_PROJECT" > /dev/null 2>&1; then
    gcloud run services delete "$SERVICE_NAME" --region="$REGION" --project="$GOOGLE_CLOUD_PROJECT" --quiet
    echo "✅ Service deleted."
else
    echo "⚠️  Service '$SERVICE_NAME' not found."
fi

echo ""
echo "[2/7] Deleting Pub/Sub Subscription..."
if gcloud pubsub subscriptions describe "$SUBSCRIPTION_ID" --project="$GOOGLE_CLOUD_PROJECT" > /dev/null 2>&1; then
    gcloud pubsub subscriptions delete "$SUBSCRIPTION_ID" --project="$GOOGLE_CLOUD_PROJECT" --quiet
    echo "✅ Subscription deleted."
else
    echo "⚠️  Subscription '$SUBSCRIPTION_ID' not found."
fi

echo ""
echo "[3/7] Deleting Pub/Sub Topic..."
if gcloud pubsub topics describe "$TOPIC_ID" --project="$GOOGLE_CLOUD_PROJECT" > /dev/null 2>&1; then
    gcloud pubsub topics delete "$TOPIC_ID" --project="$GOOGLE_CLOUD_PROJECT" --quiet
    echo "✅ Topic deleted."
else
    echo "⚠️  Topic '$TOPIC_ID' not found."
fi

echo ""
echo "[4/7] Deleting Pub/Sub Schema..."
if gcloud pubsub schemas describe "$SCHEMA_ID" --project="$GOOGLE_CLOUD_PROJECT" > /dev/null 2>&1; then
    gcloud pubsub schemas delete "$SCHEMA_ID" --project="$GOOGLE_CLOUD_PROJECT" --quiet
    echo "✅ Schema deleted."
else
    echo "⚠️  Schema '$SCHEMA_ID' not found."
fi

echo ""
echo "[5/7] Deleting BigQuery Table..."
if bq show --project_id="$GOOGLE_CLOUD_PROJECT" "${BIGQUERY_DATASET}.${BIGQUERY_TABLE}" > /dev/null 2>&1; then
    bq rm -f -t "${GOOGLE_CLOUD_PROJECT}:${BIGQUERY_DATASET}.${BIGQUERY_TABLE}"
    echo "✅ Table deleted."
else
    echo "⚠️  Table '$BIGQUERY_TABLE' not found."
fi

echo ""
echo "[6/7] Deleting BigQuery Dataset..."
if bq show --project_id="$GOOGLE_CLOUD_PROJECT" "$BIGQUERY_DATASET" > /dev/null 2>&1; then
    bq rm -f -d "${GOOGLE_CLOUD_PROJECT}:${BIGQUERY_DATASET}"
    echo "✅ Dataset deleted."
else
    echo "⚠️  Dataset '$BIGQUERY_DATASET' not found."
fi

echo ""
echo "[7/7] Deleting GCS Bucket..."
if gcloud storage buckets describe "gs://$BUCKET_NAME" --project="$GOOGLE_CLOUD_PROJECT" > /dev/null 2>&1; then
    gcloud storage rm --recursive "gs://$BUCKET_NAME" --project="$GOOGLE_CLOUD_PROJECT" --quiet
    echo "✅ Bucket deleted."
else
    echo "⚠️  Bucket 'gs://$BUCKET_NAME' not found."
fi

echo ""
echo "=================================================="
echo "✅ Cleanup complete!"
echo "=================================================="
