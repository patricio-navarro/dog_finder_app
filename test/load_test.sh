#!/bin/bash

# Ensure we are in the directory of the script to find resources
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CSV_FILE="$DIR/resources/sightings.csv"
IMAGE_DIR="$DIR/resources"
URL="https://dog-finder-app-846386313792.us-central1.run.app/submit"

if [ ! -f "$CSV_FILE" ]; then
    echo "❌ CSV file not found: $CSV_FILE"
    exit 1
fi

# Get list of images
IMAGES=("$IMAGE_DIR"/*.png)
NUM_IMAGES=${#IMAGES[@]}

if [ $NUM_IMAGES -eq 0 ]; then
    echo "❌ No images found in $IMAGE_DIR"
    exit 1
fi

echo "🚀 Starting load test..."
echo "Target: $URL"
echo "Data: $CSV_FILE"
echo "Images: $NUM_IMAGES found"

# Read CSV file, skipping header
# Use tr to remove carriage returns to handle DOS line endings
tail -n +2 "$CSV_FILE" | tr -d '\r' | while IFS=, read -r lat lng city region country date; do
    # Skip empty lines
    if [ -z "$lat" ]; then continue; fi

    # Pick a random image
    RANDOM_INDEX=$((RANDOM % NUM_IMAGES))
    IMAGE_FILE="${IMAGES[$RANDOM_INDEX]}"
    
    echo "Sending sighting: $date in $city ($lat, $lng) with image $(basename "$IMAGE_FILE")"
    
    # Send POST request
    # Added city, region, country to the request even if main.py doesn't explicitly use them yet,
    # to ensure we are sending the full dataset available.
    response=$(curl -s -w "\n%{http_code}" -X POST "$URL" \
        -F "lat=$lat" \
        -F "lng=$lng" \
        -F "city=$city" \
        -F "region=$region" \
        -F "country=$country" \
        -F "date=$date" \
        -F "image=@$IMAGE_FILE")
    
    # Parse response (macOS compatible)
    http_code=$(echo "$response" | tail -n1)
    # Remove the last line (http_code) to get the body using sed
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq 200 ]; then
        echo "✅ Success ($http_code)"
    else
        echo "❌ Failed ($http_code): $body"
    fi
    
    # Optional: sleep briefly to avoid overwhelming local docker if needed
    # sleep 0.1
done

echo "🏁 Load test complete!"
