#!/bin/bash

FILE="./migration.tar.gz"
URL="https://myntra-wishlist-discovery-engine-production.up.railway.app/api/upload-chunk"
CHUNK_SIZE=500000  # 500KB per chunk - small enough to beat any proxy limit
CHUNK_DIR="/tmp/railway_chunks"

echo "Splitting database file into 500KB chunks..."
rm -rf "$CHUNK_DIR"
mkdir -p "$CHUNK_DIR"
split -b $CHUNK_SIZE "$FILE" "$CHUNK_DIR/chunk_"

CHUNKS=("$CHUNK_DIR"/chunk_*)
TOTAL=${#CHUNKS[@]}
echo "Total chunks: $TOTAL"

for i in "${!CHUNKS[@]}"; do
    CHUNK="${CHUNKS[$i]}"
    echo "Uploading chunk $((i+1))/$TOTAL..."
    RESPONSE=$(curl --max-time 30 -s -X POST \
        --data-binary "@$CHUNK" \
        -H "Content-Type: application/octet-stream" \
        "$URL?chunk_index=$i&total_chunks=$TOTAL" 2>&1) || true
    echo "   Response: $RESPONSE"
    sleep 0.3
done

echo ""
echo "Upload sequence complete! Check the last response for success confirmation."
rm -rf "$CHUNK_DIR"
