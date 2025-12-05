#!/bin/bash
set -e

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
if [ -z "$GOOGLE_CLOUD_PROJECT" ] || [ -z "$BUCKET_NAME" ] || [ -z "$TOPIC_ID" ] || [ -z "$REGION" ] || [ -z "$BIGQUERY_DATASET" ] || [ -z "$BIGQUERY_TABLE" ]; then
    echo "❌ Missing required environment variables in .env"
    exit 1
fi

SCHEMA_ID="${TOPIC_ID}-schema"
SUBSCRIPTION_ID="${TOPIC_ID}-bq-sub"

echo "=================================================="
echo "☁️  Initializing Cloud Resources (Advanced)"
echo "Project: $GOOGLE_CLOUD_PROJECT"
echo "Region:  $REGION"
echo "Bucket:  $BUCKET_NAME"
echo "Topic:   $TOPIC_ID"
echo "Schema:  $SCHEMA_ID"
echo "BQ DS:   $BIGQUERY_DATASET"
echo "BQ Tab:  $BIGQUERY_TABLE"
echo "=================================================="

# 1. Create GCS Bucket
echo ""
echo "[1/5] Checking GCS Bucket..."
if gcloud storage buckets describe "gs://$BUCKET_NAME" --project="$GOOGLE_CLOUD_PROJECT" > /dev/null 2>&1; then
    echo "✅ Bucket 'gs://$BUCKET_NAME' already exists."
else
    echo "Creating bucket 'gs://$BUCKET_NAME'..."
    gcloud storage buckets create "gs://$BUCKET_NAME" --project="$GOOGLE_CLOUD_PROJECT" --location="$REGION"
    echo "✅ Bucket created."
fi

# 2. Create Pub/Sub Schema
echo ""
echo "[2/5] Checking Pub/Sub Schema..."
if gcloud pubsub schemas describe "$SCHEMA_ID" --project="$GOOGLE_CLOUD_PROJECT" > /dev/null 2>&1; then
    echo "✅ Schema '$SCHEMA_ID' already exists."
else
    echo "Creating schema '$SCHEMA_ID'..."
    gcloud pubsub schemas create "$SCHEMA_ID" \
        --type=avro \
        --definition-file="$PROJECT_ROOT/schemas/pubsub_schema.json" \
        --project="$GOOGLE_CLOUD_PROJECT"
    echo "✅ Schema created."
fi

# 3. Create BigQuery Dataset and Table
echo ""
echo "[3/5] Checking BigQuery Dataset & Table..."
if bq show --project_id="$GOOGLE_CLOUD_PROJECT" "$BIGQUERY_DATASET" > /dev/null 2>&1; then
    echo "✅ Dataset '$BIGQUERY_DATASET' already exists."
else
    echo "Creating dataset '$BIGQUERY_DATASET'..."
    bq --location="$REGION" mk --dataset "${GOOGLE_CLOUD_PROJECT}:${BIGQUERY_DATASET}"
    echo "✅ Dataset created."
fi

if bq show --project_id="$GOOGLE_CLOUD_PROJECT" "${BIGQUERY_DATASET}.${BIGQUERY_TABLE}" > /dev/null 2>&1; then
    echo "✅ Table '$BIGQUERY_TABLE' already exists."
else
    echo "Creating table '$BIGQUERY_TABLE'..."
    bq mk --table \
        --time_partitioning_field sighting_date \
        --time_partitioning_type DAY \
        "${GOOGLE_CLOUD_PROJECT}:${BIGQUERY_DATASET}.${BIGQUERY_TABLE}" \
        "$PROJECT_ROOT/schemas/bigquery_schema.json"
    echo "✅ Table created."
fi

# 4. Create Pub/Sub Topic with Schema
echo ""
echo "[4/5] Checking Pub/Sub Topic..."
if gcloud pubsub topics describe "$TOPIC_ID" --project="$GOOGLE_CLOUD_PROJECT" > /dev/null 2>&1; then
    echo "✅ Topic '$TOPIC_ID' already exists."
    # Note: Updating schema on existing topic is complex/limited. Assuming it matches if exists.
else
    echo "Creating topic '$TOPIC_ID' with schema..."
    gcloud pubsub topics create "$TOPIC_ID" \
        --schema="$SCHEMA_ID" \
        --message-encoding=json \
        --project="$GOOGLE_CLOUD_PROJECT"
    echo "✅ Topic created."
fi

# 5. Create BigQuery Subscription
echo ""
echo "[5/5] Checking BigQuery Subscription..."
if gcloud pubsub subscriptions describe "$SUBSCRIPTION_ID" --project="$GOOGLE_CLOUD_PROJECT" > /dev/null 2>&1; then
    echo "✅ Subscription '$SUBSCRIPTION_ID' already exists."
else
    echo "Creating subscription '$SUBSCRIPTION_ID'..."
    gcloud pubsub subscriptions create "$SUBSCRIPTION_ID" \
        --topic="$TOPIC_ID" \
        --bigquery-table="${GOOGLE_CLOUD_PROJECT}:${BIGQUERY_DATASET}.${BIGQUERY_TABLE}" \
        --use-topic-schema \
        --write-metadata \
        --project="$GOOGLE_CLOUD_PROJECT"
    echo "✅ Subscription created."
fi

echo ""
echo "=================================================="
echo "🎉 Advanced setup complete!"
echo "=================================================="
