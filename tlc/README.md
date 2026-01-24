# TLC Trip Data - Download Scripts

This folder contains scripts for downloading and managing NYC TLC (Taxi & Limousine Commission) trip data.

## Overview

The scripts download historical trip data for four vehicle types:
- **Yellow Taxis** - traditional NYC yellow cabs
- **Green Taxis** - street-hail livery vehicles (primarily outer boroughs)
- **FHV** - For-Hire Vehicles (black cars, livery)
- **FHVHV** - High-Volume For-Hire Vehicles (Uber, Lyft, etc.)

## Scripts

### 1. download_tlc_data.sh
Downloads TLC trip data parquet files from 2021-2025.

**Usage:**
```bash
./download_tlc_data.sh
```

**Features:**
- Downloads all 4 trip types for years 2021-2025
- Approximately 240 files total
- Skips files that already exist (resume capability)
- Rate limiting (3 seconds between downloads) to avoid CloudFront 403 errors
- Shows progress with file sizes

**Expected Output:**
- Files named like: `yellow_tripdata_2024-01.parquet`
- Total size: ~29GB
- Some months may not exist (returns 404) - this is normal

**Notes:**
- Download takes ~30-45 minutes with rate limiting
- Files are stored in current directory (tlc/)
- Safe to stop and restart - will resume from where it left off

---

### 2. check_size.sh
Analyzes storage usage of downloaded parquet files.

**Usage:**
```bash
./check_size.sh
```

**Output:**
```
==========================================
TLC Data Storage Analysis
==========================================

File Counts:
  Yellow:  59 files
  Green:   59 files
  FHV:     58 files
  FHVHV:   59 files
  Total:   235 files

Yellow trips:  3.0G
Green trips:    82M
FHV trips:     867M
FHVHV trips:   25G

==========================================
TOTAL SIZE:     29G
==========================================
```

**Use Cases:**
- Check download progress
- Verify disk space usage
- Confirm all files downloaded successfully

---

## Data Loading

After downloading, load data into PostgreSQL using the backend scripts:

```bash
cd ../backend

# Load all data
export DATABASE_URL="postgresql://user:pass@host:5432/nycdb?sslmode=require"
python3 load_data.py --data-dir ../tlc

# Load specific year only
python3 load_data.py --data-dir ../tlc --year 2024

# Load specific trip types
python3 load_data.py --data-dir ../tlc --trip-types yellow green

# View statistics only (no loading)
python3 load_data.py --stats-only
```

## File Structure

```
tlc/
├── README.md                           # This file
├── download_tlc_data.sh               # Download script
├── check_size.sh                      # Size analysis script
├── yellow_tripdata_2021-10.parquet    # Example data file
├── green_tripdata_2024-01.parquet     # Example data file
└── ...                                # More parquet files
```

## Data Sources

All data is downloaded from the official NYC TLC CloudFront CDN:
- Base URL: https://d37ci6vzurychx.cloudfront.net/trip-data
- Format: Parquet (columnar storage, efficient compression)
- Update frequency: Monthly

## Troubleshooting

**403 CloudFront Error:**
- Script already has 3-second delays to prevent this
- If still occurring, increase sleep time in download_tlc_data.sh

**404 File Not Found:**
- Normal - not all months have data available
- Early 2021 months (Jan-Sep) don't exist for most trip types
- Script continues with other files

**Disk Space:**
- Full dataset: ~29GB
- Ensure you have at least 35GB free space
- Use check_size.sh to monitor usage

**Resume Download:**
- Script automatically skips existing files
- Just run ./download_tlc_data.sh again

## Data Schema

See [backend/models.py](../backend/models.py) for complete PostgreSQL schema definitions.

**Yellow/Green Trips:**
- Pickup/dropoff datetime and locations
- Fare breakdown (base, tips, tolls, surcharges)
- Trip distance and passenger count

**FHV Trips:**
- Pickup/dropoff datetime and locations
- Dispatching base information
- Shared ride flag

**FHVHV Trips (Uber/Lyft):**
- Request/pickup/dropoff times
- Fare components and driver pay
- Trip distance and time
- Shared ride and accessibility flags

## Next Steps

1. Download data: `./download_tlc_data.sh`
2. Check progress: `./check_size.sh`
3. Load into database: `cd ../backend && python3 load_data.py --data-dir ../tlc`
4. Query via API: Backend will have endpoints for analytics

## Resources

- [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page)
- [Data Dictionary](https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf)
- [TLC Website](https://www.nyc.gov/site/tlc/)
