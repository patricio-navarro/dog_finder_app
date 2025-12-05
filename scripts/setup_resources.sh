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

# 1b. Make Bucket Public (User Request for Reliability)
echo "Ensuring Bucket is Public..."
gcloud storage buckets add-iam-policy-binding "gs://$BUCKET_NAME" \
    --member="allUsers" \
    --role="roles/storage.objectViewer" \
    --project="$GOOGLE_CLOUD_PROJECT"
echo "✅ Bucket is now public."

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

# 6. Create Firestore Database (Native Mode)
echo ""
echo "[6/6] Checking Firestore Database..."
# Check if default database exists
if gcloud firestore databases list --project="$GOOGLE_CLOUD_PROJECT" --format="value(name)" | grep -q "projects/$GOOGLE_CLOUD_PROJECT/databases/(default)"; then
    echo "✅ Firestore database '(default)' already exists."
else
    echo "Creating Firestore database '(default)'..."
    gcloud firestore databases create --location="$REGION" --type=firestore-native --project="$GOOGLE_CLOUD_PROJECT"
    echo "✅ Firestore database created."
fi

# 7. Create Firestore Composite Index
echo ""
echo "[7/7] Checking Firestore Indexes..."
# We try to create it. If it exists, it returns a message but exits 0 or similar (or we can ignore "already exists" error).
# The most robust way is to just run it and catch failure if it's "Already exists", but gcloud might fail hard.
# Let's check if we can list it, but list parsing is annoying. 
# We'll just run 'create' which is idempotent-ish enough or we suppress error if it says "already exists".
echo "Ensuring Composite Index exists..."
gcloud firestore indexes composite create \
    --collection-group=sightings \
    --field-config field-path=sighting_date,order=descending \
    --field-config field-path=timestamp,order=descending \
    --project="$GOOGLE_CLOUD_PROJECT" \
    --quiet || echo "⚠️ Index creation might have failed or already exists. Check Console if search fails."

# 8. Grant Service Account Token Creator Role (For Signed URLs)
echo ""
echo "[8/8] Checking IAM Permissions..."
PROJECT_NUMBER=$(gcloud projects describe "$GOOGLE_CLOUD_PROJECT" --format="value(projectNumber)")
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting 'Service Account Token Creator' to $SERVICE_ACCOUNT..."
gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --condition=None \
    --quiet > /dev/null 2>&1
echo "✅ IAM role granted."

echo ""
echo "=================================================="
echo "🎉 Advanced setup complete!"
echo "=================================================="
