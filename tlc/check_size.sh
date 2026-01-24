#!/bin/bash

# Script to check total size of downloaded TLC data files

echo "=========================================="
echo "TLC Data Storage Analysis"
echo "=========================================="
echo ""

# Count files by type
YELLOW_COUNT=$(ls -1 yellow_tripdata_*.parquet 2>/dev/null | wc -l | tr -d ' ')
GREEN_COUNT=$(ls -1 green_tripdata_*.parquet 2>/dev/null | wc -l | tr -d ' ')
FHV_COUNT=$(ls -1 fhv_tripdata_*.parquet 2>/dev/null | wc -l | tr -d ' ')
FHVHV_COUNT=$(ls -1 fhvhv_tripdata_*.parquet 2>/dev/null | wc -l | tr -d ' ')
TOTAL_FILES=$((YELLOW_COUNT + GREEN_COUNT + FHV_COUNT + FHVHV_COUNT))

echo "File Counts:"
echo "  Yellow:  $YELLOW_COUNT files"
echo "  Green:   $GREEN_COUNT files"
echo "  FHV:     $FHV_COUNT files"
echo "  FHVHV:   $FHVHV_COUNT files"
echo "  Total:   $TOTAL_FILES files"
echo ""

# Calculate sizes by type
if [ $YELLOW_COUNT -gt 0 ]; then
    YELLOW_SIZE=$(du -ch yellow_tripdata_*.parquet 2>/dev/null | tail -1 | cut -f1)
    echo "Yellow trips:  $YELLOW_SIZE"
fi

if [ $GREEN_COUNT -gt 0 ]; then
    GREEN_SIZE=$(du -ch green_tripdata_*.parquet 2>/dev/null | tail -1 | cut -f1)
    echo "Green trips:   $GREEN_SIZE"
fi

if [ $FHV_COUNT -gt 0 ]; then
    FHV_SIZE=$(du -ch fhv_tripdata_*.parquet 2>/dev/null | tail -1 | cut -f1)
    echo "FHV trips:     $FHV_SIZE"
fi

if [ $FHVHV_COUNT -gt 0 ]; then
    FHVHV_SIZE=$(du -ch fhvhv_tripdata_*.parquet 2>/dev/null | tail -1 | cut -f1)
    echo "FHVHV trips:   $FHVHV_SIZE"
fi

echo ""
echo "=========================================="

# Total size of all parquet files
if [ $TOTAL_FILES -gt 0 ]; then
    TOTAL_SIZE=$(du -ch *.parquet 2>/dev/null | tail -1 | cut -f1)
    echo "TOTAL SIZE:    $TOTAL_SIZE"
else
    echo "No parquet files found"
fi

echo "=========================================="
