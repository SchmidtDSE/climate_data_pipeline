#!/bin/bash

# Script to download climate TIF files from Google Cloud Storage
# Source: gs://national_park_service/CHC_CMIP6/

# Set variables
BASE_URL="https://storage.googleapis.com/national_park_service/CHC_CMIP6"
OUTPUT_DIR="./climate_data"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

echo "Starting download of climate TIF files..."
echo "Output directory: $OUTPUT_DIR"
echo ""

# Get list of all TIF files
echo "Fetching file list..."
FILES=$(gsutil ls gs://national_park_service/CHC_CMIP6/*.tif | sed 's|gs://national_park_service/CHC_CMIP6/||')

# Count total files
TOTAL=$(echo "$FILES" | wc -l)
CURRENT=0

echo "Found $TOTAL files to download"
echo ""

# Download each file
for FILE in $FILES; do
    CURRENT=$((CURRENT + 1))
    echo "[$CURRENT/$TOTAL] Downloading: $FILE"

    wget -q --show-progress \
        -O "$OUTPUT_DIR/$FILE" \
        "$BASE_URL/$FILE"

    if [ $? -eq 0 ]; then
        echo "  ✓ Successfully downloaded: $FILE"
    else
        echo "  ✗ Failed to download: $FILE"
    fi
    echo ""
done

echo "Download complete!"
echo "Files saved to: $OUTPUT_DIR"
