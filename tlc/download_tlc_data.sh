#!/bin/bash

# Script to download TLC trip data for 2021-2025
# All 4 trip types: yellow, green, fhv, fhvhv

BASE_URL="https://d37ci6vzurychx.cloudfront.net/trip-data"
TYPES=("yellow" "green" "fhv" "fhvhv")
START_YEAR=2021
END_YEAR=2025

echo "Starting download of TLC trip data (2021-2025)..."
echo "This will download approximately 240 files"
echo ""

DOWNLOADED=0
FAILED=0

for YEAR in $(seq $START_YEAR $END_YEAR); do
    for MONTH_NUM in {1..12}; do
        MONTH=$(printf "%02d" $MONTH_NUM)
        for TYPE in "${TYPES[@]}"; do
            FILENAME="${TYPE}_tripdata_${YEAR}-${MONTH}.parquet"
            URL="${BASE_URL}/${FILENAME}"
            
            # Skip if file already exists
            if [ -f "$FILENAME" ]; then
                echo "✓ Already exists: $FILENAME"
                ((DOWNLOADED++))
                continue
            fi
            
            echo "Downloading: $FILENAME"
            if curl -f -L -o "$FILENAME" "$URL" 2>/dev/null; then
                echo "✓ Downloaded: $FILENAME ($(du -h "$FILENAME" | cut -f1))"
                ((DOWNLOADED++))
                # Add delay to avoid rate limiting (3 seconds between successful downloads)
                sleep 3
            else
                echo "✗ Failed: $FILENAME (file may not exist)"
                ((FAILED++))
                # Shorter delay for failed requests
                sleep 1
            fi
        done
    done
done

echo ""
echo "=========================================="
echo "Download Complete!"
echo "Downloaded: $DOWNLOADED files"
echo "Failed: $FAILED files"
echo "=========================================="
