# Azure Container Data Loader - Setup & Usage Guide

## ✅ Current Status

**Storage Account:** `nycdevdata` (already created)  
**Container:** `tlc-data` (files uploaded: 235 parquet + 1 CSV)  
**Container App:** `nyc-data-loader-job` (deployed)  
**Current Execution:** Running with duplicate prevention

---

## Quick Reference Commands

### Monitor Running Job
```bash
# Check job status
az containerapp job execution list \
  --name nyc-data-loader-job \
  --resource-group nyc-dev-rg \
  --output table

# View latest logs (replace execution name with current one)
az containerapp job logs show \
  --name nyc-data-loader-job \
  --resource-group nyc-dev-rg \
  --execution <execution-name> \
  --container nyc-data-loader-job \
  --tail 50

# Check database stats
python3 load_data_safe.py --stats-only
```

### Start New Job Execution
```bash
az containerapp job start \
  --name nyc-data-loader-job \
  --resource-group nyc-dev-rg
```

### Stop Running Execution
```bash
az containerapp job stop \
  --name nyc-data-loader-job \
  --resource-group nyc-dev-rg \
  --job-execution-name <execution-name>
```

---

## Initial Setup (Already Completed)

### 1a. Storage Account Created
- **Name:** nycdevdata
- **Resource Group:** nyc-dev-rg
- **Region:** West US
- **Container:** tlc-data

### 1b. Files Uploaded

### 1b. Files Uploaded
- ✅ 235 parquet files (yellow, green, fhv, fhvhv trip data)
- ✅ 1 CSV file (taxi_zone_lookup.csv)
- **Total:** ~50GB of data

### 1c. Connection String
```
DefaultEndpointsProtocol=https;AccountName=nycdevdata;AccountKey=w8EFKLgIwfnEe7RGnXUnOrlkpFxi/BP6O4G3toNumv/3EeLqs6BF4RRIu3DuRCKhebkj94AeMCAy+AStL3p5kA==;EndpointSuffix=core.windows.net
```

---

## Duplicate Prevention Features

The loader has built-in duplicate prevention:
- ✅ **File Tracking:** Creates `loaded_files` table to track processed files
- ✅ **Skip Loaded Files:** Automatically skips files already in database
- ✅ **Taxi Zone Check:** Won't reload taxi zones if already present (265 zones)
- ✅ **Safe for Multiple Runs:** Can restart job without duplicating data

---

## Architecture

**Container App Job:** `nyc-data-loader-job`
- **Image:** nycacrtakkd33nvzu2k.azurecr.io/nyc-data-loader:latest
- **Resources:** 4 CPUs, 8GB RAM
- **Workers:** 3 parallel workers
- **Timeout:** 7200 seconds (2 hours)
- **Environment:** nyc-dev-env (West US)

**Loading Process:**
1. Checks if taxi zones exist (skips if 265 already loaded)
2. Downloads parquet files from blob storage to `/tmp/data`
3. Loads data using PostgreSQL COPY command (fast bulk insert)
4. Deletes temp file after loading
5. Marks file as loaded in tracking table
6. Processes files in parallel (3 workers)

---

## Manual Setup Instructions (if needed)

### Upload Additional Files

### Upload Additional Files

**Method A: Azure Storage Explorer (Recommended)**
1. Download: https://azure.microsoft.com/features/storage-explorer/
2. Sign in with Azure account
3. Navigate to: **nycdevdata → Blob Containers → tlc-data**
4. Upload files (parallel transfers, fast)

**Method B: Azure CLI**
```bash
export AZURE_STORAGE_CONNECTION_STRING="<connection-string>"
az storage blob upload \
  --container-name tlc-data \
  --file <local-file-path> \
  --name <blob-name> \
  --overwrite
```

### Rebuild & Redeploy Container

If you need to update the loader code:
```bash
cd /Users/joshperryman/NewAge/nyc/backend

# Rebuild for AMD64 (Azure compatible)
docker buildx build --platform linux/amd64 \
  -t nycacrtakkd33nvzu2k.azurecr.io/nyc-data-loader:latest \
  -f Dockerfile.dataloader .

# Push to ACR
docker push nycacrtakkd33nvzu2k.azurecr.io/nyc-data-loader:latest

# Container App automatically uses new image on next execution
```

---

## Performance Metrics

**Local Loading (from Mac):**
- Latency: 50-100ms per batch
- Speed: ~800k-1.5M records/min
- Time for all data: 3-4 hours

**Azure Container Loading (in-region):**
- Latency: <1ms per batch
- Speed: ~5-10M records/min ⚡
- Time for all data: **30-60 minutes**
- **10-20x faster!**

---

## Monitoring Progress

## Monitoring Progress

### Check Job Status
```bash
az containerapp job execution list \
  --name nyc-data-loader-job \
  --resource-group nyc-dev-rg \
  --output table
```

### View Logs
```bash
# Replace <execution-name> with actual execution name from list command
az containerapp job logs show \
  --name nyc-data-loader-job \
  --resource-group nyc-dev-rg \
  --execution <execution-name> \
  --container nyc-data-loader-job \
  --tail 100
```

### Check Database Progress
```bash
cd /Users/joshperryman/NewAge/nyc/backend
export DATABASE_URL="postgresql://..."

# Show current record counts
python3 load_data_safe.py --stats-only

# Show which files have been loaded
python3 load_data_safe.py --show-loaded
```

### What to Expect in Logs
```
✓ Taxi zones already loaded (265 zones)

YELLOW TRIPS
Found 59 files
✓ yellow_tripdata_2023-01.parquet: 3,066,766 records in 12.3s (249,328 rec/s)
⏭️ Skipping yellow_tripdata_2023-02.parquet (already loaded)
✓ yellow_tripdata_2023-03.parquet: 3,413,784 records in 13.8s (247,376 rec/s)
...
```

---

## Local Alternative Loader

You can also use the safe loader locally (it has same duplicate prevention):

```bash
cd /Users/joshperryman/NewAge/nyc/backend
export DATABASE_URL="postgresql://..."

# Load all data (skips duplicates)
python3 load_data_safe.py

# Load specific trip types
python3 load_data_safe.py --trip-types yellow green
```

Both loaders share the same `loaded_files` tracking table, so they won't conflict!

---

## Expected Timeline

**All 235 Files (~140M records):**
- Yellow trips: 59 files (~28M records) - 15-20 min
- Green trips: 59 files (~15M records) - 10-15 min
- FHV trips: 59 files (~40M records) - 20-25 min
- FHVHV trips: 58 files (~57M records) - 25-30 min

**Total: ~60-90 minutes** in Azure vs 3-4 hours locally

---

## Troubleshooting

### Job Shows "Running" But No Logs
- Wait 30-60 seconds for logs to appear
- Container might be downloading files
- Check again with tail parameter: `--tail 100`

### "Already Loaded" Messages
- ✅ This is normal! Duplicate prevention working
- Loader skips files already in database
- Check `loaded_files` table to see what's been processed

### Container Fails to Start
- Verify DATABASE_URL secret is correct
- Check storage connection string secret
- View job configuration:
  ```bash
  az containerapp job show \
    --name nyc-data-loader-job \
    --resource-group nyc-dev-rg
  ```

### Slow Loading Speed
- Expected: 5-10M records/min in Azure
- If slower: check database connection in logs
- Azure internal network should be <1ms latency

### Want to Reload Specific Files
```bash
# Connect to database
psql "$DATABASE_URL"

# Remove file from tracking table
DELETE FROM loaded_files WHERE filename = 'yellow_tripdata_2023-01.parquet';

# Start new job execution - it will reload that file
```

---

## Cost Considerations

**Container App Job:**
- Only charged when running (manual trigger)
- 4 vCPU + 8GB RAM = ~$0.17/hour
- 1-hour run ≈ $0.17
- Much cheaper than keeping Mac running for 3-4 hours!

**Storage:**
- 50GB @ $0.02/GB/month = $1/month
- Can delete after loading if needed

**Total cost for one-time load:** < $1

