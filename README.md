# NYC Taxi Trip Analytics Platform

A production-ready, full-stack analytics platform for NYC TLC (Taxi & Limousine Commission) trip data. Features real-time dashboards, time-series visualizations, and efficient bulk data processing with PostgreSQL materialized views.

## Features

- **Real-time Analytics Dashboard** - Interactive charts showing daily trip patterns and revenue trends
- **High-Performance Data Loading** - PostgreSQL COPY command for 3-5x faster bulk imports
- **Materialized Views** - Pre-computed daily aggregates for lightning-fast queries
- **Zone Enrichment** - Trip data enriched with NYC borough and zone information
- **RESTful API** - Comprehensive endpoints with pagination and filtering
- **Time-Series Charts** - Chart.js visualizations with color-coded trip types
- **Date Filtering** - Flexible date range selection and trip type filtering
- **Scalable Architecture** - Deployed on Azure with CI/CD pipelines
- **API Security** - Rate limiting (100 req/min) and CORS protection

## Security Approach

This platform uses **rate limiting** and **CORS protection** for API security rather than API key authentication. This design choice is intentional for several reasons:

1. **Public Analytics Use Case** - The platform provides public NYC trip data analytics. There's no sensitive user data or private information that requires authentication.

2. **Frontend Security Limitation** - API keys stored in frontend JavaScript would be exposed in the browser, providing no real security benefit. Any user could inspect the network requests and extract the key.

3. **Avoiding Unnecessary Complexity** - Implementing API key security for a frontend application would require:
   - A backend proxy/BFF (Backend-for-Frontend) to hide the keys
   - Additional service deployment and maintenance
   - Extra network hops and latency
   - More complex CI/CD pipelines

4. **Rate Limiting is Sufficient** - The 100 requests/minute rate limit effectively prevents abuse while allowing legitimate users full access to the analytics dashboard.

5. **Standard Pattern for Public APIs** - Many public analytics and data visualization platforms use this same approach (rate limiting without authentication) when serving public datasets.

**If you need user-specific access control**, consider implementing session-based authentication with HttpOnly cookies instead of API keys. This provides real security without exposing credentials in the frontend.

## Architecture

- **Backend**: FastAPI (Python 3.11) with SQLAlchemy ORM and Pydantic validation
- **Frontend**: Angular 17 with standalone components and Chart.js 4.5
- **Database**: Azure PostgreSQL 16 Flexible Server with materialized views
- **Container Registry**: Azure Container Registry (ACR)
- **Hosting**: Azure Container Apps (Backend) + Static Web App (Frontend potential)
- **CI/CD**: GitHub Actions for automated deployment
- **Data Format**: Parquet files with pandas/pyarrow processing

## Project Structure

```
nyc/
├── backend/                      # FastAPI backend
│   ├── main.py                   # API endpoints and application
│   ├── models.py                 # SQLAlchemy ORM models
│   ├── database.py               # Database connection
│   ├── init-local-db.sql         # Auto-executed schema initialization
│   ├── create_schema.py          # Schema creation (Azure deployment)
│   ├── load_data.py              # Data loader (Cloud version)
│   ├── start-backend.sh          # Auto-setup script (venv, deps, server)
│   └── requirements.txt          # Python dependencies
├── frontend/                     # Angular standalone frontend
│   ├── src/
│   │   └── app/
│   │       └── app.component.ts  # Main dashboard component (Chart.js)
│   ├── package.json              # Node dependencies
│   └── angular.json              # Angular configuration
├── infra/                        # Azure Bicep infrastructure
│   ├── main.bicep                # Main infrastructure template
│   ├── resources.bicep           # Resource definitions (Storage + Job)
│   └── main.bicepparam           # Parameters
├── tlc/                          # Local TLC trip data files
│   ├── taxi_zone_lookup.csv      # 265 NYC taxi zones
│   ├── yellow_tripdata_*.parquet # Yellow taxi trip records (2021-2025)
│   ├── green_tripdata_*.parquet  # Green taxi trip records (2021-2025)
│   ├── fhv_tripdata_*.parquet    # FHV trip records (2021-2025)
│   └── fhvhv_tripdata_*.parquet  # FHVHV trip records (2021-2025)
├── setup-local-dev.sh            # One-command local environment setup
├── package.json                  # Root npm scripts (orchestration)
└── docker-compose.yml            # PostgreSQL service definition
```

**Key Files:**
- [backend/init-local-db.sql](backend/init-local-db.sql) - Auto-executed by PostgreSQL on container start (tables, indexes, materialized views)
- [setup-local-dev.sh](setup-local-dev.sh) - Orchestrates database start, data loading, and view refresh
- [backend/start-backend.sh](backend/start-backend.sh) - Auto-creates venv, installs deps, starts FastAPI
- [package.json](package.json) - Root-level npm scripts for one-command workflow
├── tlc/                 # TLC data storage
│   ├── download_tlc_data.sh  # Data download script
│   └── *.parquet        # Trip data files (235 files)
├── docs/                # Documentation
│   ├── API_DOCUMENTATION.md  # API endpoints and usage
│   ├── DEPLOYMENT.md    # Azure deployment guide
│   ├── SECURITY.md      # Security configuration
│   └── TESTING.md       # Testing documentation
├── .github/
│   └── workflows/       # CI/CD pipelines
└── docker-compose.yml   # Local development setup
```

## Documentation

- **[API Documentation](docs/API_DOCUMENTATION.md)** - Complete API endpoint reference with examples
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Multi-environment Azure deployment with GitHub Actions
- **[Security Configuration](docs/SECURITY.md)** - Rate limiting, CORS, and security best practices
- **[Testing Guide](docs/TESTING.md)** - Backend and frontend test suites with coverage reports
- **[TLC Data](tlc/README.md)** - Download scripts and data management

---

## Local Development

### Quick Start (One Command)

Start everything with a single command:

```bash
# Install dependencies (first time only)
npm install

# One-command startup (recommended)
npm start
```

This single command will:
1. ✅ Start PostgreSQL in Docker (with clean slate)
2. ✅ Auto-initialize database schema on container start
3. ✅ Load taxi zone lookup data (265 zones)
4. ✅ Load 12,000 sample trip records from local files
5. ✅ Refresh materialized views for performance
6. ✅ Start backend API on http://localhost:8000
7. ✅ Start frontend on http://localhost:4200

**What's happening behind the scenes:**
- `docker-compose down -v && docker-compose up -d` - Clean database start
- PostgreSQL executes [backend/init-local-db.sql](backend/init-local-db.sql) automatically on container initialization
- [setup-local-dev.sh](setup-local-dev.sh) loads sample data from local `/tlc` folder (no downloads needed)
- Materialized views (`trip_summary_view`, `daily_trip_aggregates`) are refreshed after data load
- Backend auto-creates Python venv, installs dependencies, and starts FastAPI server
- Frontend builds and serves Angular application with hot reload

**Sample Data Included:**
- 3,000 Yellow Taxi trips (Jan-Mar 2025, 1000/month)
- 3,000 Green Taxi trips (Jan-Mar 2025, 1000/month)
- 3,000 FHV trips (Jan-Mar 2025, 1000/month)
- 3,000 FHVHV trips (Jan-Mar 2025, 1000/month)
- 265 Taxi Zone reference data
- **Total: 12,000 trip records**

**Other useful commands:**
```bash
# Start services without database reset (faster)
npm run dev

# Individual services
npm run backend      # Start backend only
npm run frontend     # Start frontend only

# Database management
docker-compose down          # Stop database
docker-compose down -v       # Stop and delete database volume
docker-compose up -d         # Start database only
```

**Local Services:**
- Frontend: http://localhost:4200
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: postgresql://postgres:postgres@localhost:5432/nycdb

### Architecture Notes

**Materialized Views for Performance:**
The application uses PostgreSQL materialized views to pre-compute expensive queries:
- `trip_summary_view` - Unified view of all trip types with zone information
- `daily_trip_aggregates` - Pre-computed daily statistics (trip counts, fares, distances)

These views are created with `WITH NO DATA` during schema initialization and refreshed after loading sample data. This pattern ensures fast API response times for dashboard queries.

**Automated Schema Management:**
The database schema is automatically initialized when PostgreSQL starts via [backend/init-local-db.sql](backend/init-local-db.sql). This includes:
- 6 tables: yellow_trips, green_trips, fhv_trips, fhvhv_trips, taxi_zone_lookup, loaded_files
- Indexes for query optimization
- Triggers for data validation
- Materialized views for performance
- Support for 2025 data format (includes `cbd_congestion_fee` column)

### Prerequisites

- **Docker Desktop** (for local PostgreSQL container)
- **Node.js 20+** (for npm scripts and frontend)
- **Python 3.11+** (auto-managed by backend startup script)

### Troubleshooting

**Database connection errors:**
```bash
# Check if PostgreSQL is running
docker ps

# View database logs
docker-compose logs db

# Restart database with clean slate
docker-compose down -v && docker-compose up -d
```

**Backend startup errors:**
```bash
# View backend logs
cd backend
cat setup.log

# Manually start backend to see detailed errors
./start-backend.sh
```

**Port already in use:**
```bash
# Find process using port 8000 or 4200
lsof -ti:8000 | xargs kill -9
lsof -ti:4200 | xargs kill -9

# Then restart
npm start
```

**Materialized views not refreshing:**
```bash
# Connect to database
docker exec -it nyc-db-1 psql -U postgres -d nycdb

# Refresh views manually
REFRESH MATERIALIZED VIEW trip_summary_view;
REFRESH MATERIALIZED VIEW daily_trip_aggregates;
```

### Manual Backend Development

If you prefer to run backend manually instead of using `npm start`:

```bash
cd backend

# Create virtual environment (first time)
python3 -m venv venv
source venv/bin/activate
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start local database (if not already running)
docker-compose up -d db

# Database will auto-connect to local: postgresql://postgres:postgres@localhost:5432/nycdb
# Or set custom connection:
# export DATABASE_URL="postgresql://user:password@host:5432/nycdb"

# Initialize schema
python create_schema.py

# Start development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Backend will be available at:**
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Manual Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

**Frontend will be available at:** http://localhost:4200

The frontend dashboard includes:
- Time-series charts for daily trips and revenue
- Date range filtering
- Trip type selection (Yellow, Green, FHV, FHVHV)
- Paginated trip data tables
- Summary statistics cards

### Environment Variables

#### Backend (.env or export)

```bash
DATABASE_URL=postgresql://user:password@host:5432/nycdb?sslmode=require
PORT=8000

# Security Configuration
CORS_ORIGINS=http://localhost:4200,http://localhost:3000
RATE_LIMIT_PER_MINUTE=100
```

**Security Notes:**
- `CORS_ORIGINS`: Comma-separated list of additional allowed origins
- Azure Container Apps URLs (`https://nyc-*-frontend.*-*.westus.azurecontainerapps.io`) are automatically allowed via regex
- **Custom Domains**: If you have custom domains, you must add them to `CORS_ORIGINS` (e.g., `https://your-domain.com`)
- `RATE_LIMIT_PER_MINUTE`: API rate limit per IP address (default: 100)
- See [SECURITY.md](docs/SECURITY.md) for comprehensive security documentation

#### Frontend

Update [src/environments/environment.ts](frontend/src/environments/environment.ts):

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000'
};
```

For production, update [environment.prod.ts](frontend/src/environments/environment.prod.ts):

```typescript
export const environment = {
  production: true,
  apiUrl: 'https://your-backend-url.azurecontainerapps.io'
};
```

---

## Azure Deployment

### Infrastructure Overview

The application is deployed on Azure using:
- **Azure Container Apps** - Serverless backend hosting
- **Azure PostgreSQL Flexible Server** - Managed database (16)
- **Azure Container Registry** - Docker image storage
- **Azure Key Vault** - Secrets management
- **GitHub Actions** - CI/CD automation

### 1. Deploy Infrastructure

Deploy using Bicep templates:

```bash
cd infra

# Login to Azure
az login

# Create resource group and deploy
az deployment sub create \
  --location eastus \
  --template-file main.bicep \
  --parameters main.bicepparam \
  --parameters environmentName=nyc-prod
```

This creates:
- Resource group: `rg-nyc-prod`
- PostgreSQL server: `nyc-prod-db{uniqueid}.postgres.database.azure.com`
- Container registry: `nycacr{uniqueid}.azurecr.io`
- Container app environment and backend app
- **Storage account**: `nycproddata{uniqueid}` with `tlc-data` blob container (automatically created)
- **Container app job**: `nyc-prod-data-loader-job` for fast data loading (automatically created)
- Key Vault: `nyc-prod-kv{uniqueid}`
- Log Analytics workspace

**Important Outputs:**
```bash
# Get storage account details for data upload
az deployment sub show \
  --name {deployment-name} \
  --query "properties.outputs" -o json

# You'll need:
# - storageAccountName: For uploading data files
# - dataLoaderJobName: For starting the data load
```

### 2. Configure GitHub Secrets

Add the following secrets to your GitHub repository (Settings → Secrets → Actions):

```bash
# Get Azure credentials
az ad sp create-for-rbac --name "github-nyc-deploy" \
  --role contributor \
  --scopes /subscriptions/{subscription-id} \
  --sdk-auth

# Add to GitHub as: AZURE_CREDENTIALS
```

Additional secrets needed:
- `ACR_LOGIN_SERVER`: `{acrname}.azurecr.io` (from deployment output)
- `ACR_USERNAME`: ACR admin username
- `ACR_PASSWORD`: ACR admin password (enable in ACR → Access keys)

### 3. Deploy Application

Push to the `main` branch to trigger automatic deployment via GitHub Actions:

```bash
git checkout main
git merge develop
git push origin main
```

The CI/CD pipeline will:
1. Build backend Docker image
2. Push to Azure Container Registry
3. Deploy new revision to Container Apps
4. Build and deploy frontend (if configured)

### 4. Database Connection

Retrieve database password from Key Vault:

```bash
az keyvault secret show \
  --vault-name nyc-prod-kv{uniqueid} \
  --name db-password \
  --query "value" -o tsv
```

Connection string format:
```
postgresql://nycadmin:{password}@{server}.postgres.database.azure.com:5432/nycdb?sslmode=require
```

### 5. Load Data to Azure

**Recommended: Azure Container Loader** (see [Data Loading](#data-loading-critical-performance-information))

The infrastructure automatically creates a storage account and container app job for fast data loading. You only need to upload the parquet files:

**Step 1: Download TLC Data Locally**
```bash
cd tlc
./download_tlc_data.sh
# Downloads 235 parquet files (~50GB) to ./data/
```

**Step 2: Upload Files to Azure Blob Storage**

Option A - Using Azure Storage Explorer (GUI):
1. Download [Azure Storage Explorer](https://azure.microsoft.com/features/storage-explorer/)
2. Connect to your Azure subscription
3. Navigate to storage account: `nycproddata{uniqueid}`
4. Open blob container: `tlc-data`
5. Upload all files from `tlc/data/` directory

Option B - Using Azure CLI (Batch Upload):
```bash
# Get storage account name from deployment output
STORAGE_ACCOUNT=$(az deployment sub show \
  --name {deployment-name} \
  --query "properties.outputs.storageAccountName.value" -o tsv)

# Upload all files (takes 30-60 minutes)
az storage blob upload-batch \
  --account-name $STORAGE_ACCOUNT \
  --destination tlc-data \
  --source tlc/data/ \
  --pattern "*.parquet" \
  --auth-mode login
  
# Upload taxi zone lookup
az storage blob upload \
  --account-name $STORAGE_ACCOUNT \
  --container-name tlc-data \
  --file tlc/data/taxi_zone_lookup.csv \
  --name taxi_zone_lookup.csv \
  --auth-mode login
```

Option C - Using AzCopy (Fastest):
```bash
# Install AzCopy: https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-v10

# Get storage account connection details
STORAGE_ACCOUNT=$(az deployment sub show \
  --name {deployment-name} \
  --query "properties.outputs.storageAccountName.value" -o tsv)

# Upload with AzCopy (10-20 minutes with good connection)
azcopy copy "tlc/data/*" \
  "https://${STORAGE_ACCOUNT}.blob.core.windows.net/tlc-data/" \
  --recursive
```

**Step 3: Start Data Loading Job**
```bash
# Get job name from deployment output
JOB_NAME=$(az deployment sub show \
  --name {deployment-name} \
  --query "properties.outputs.dataLoaderJobName.value" -o tsv)

# Get resource group
RG_NAME="rg-nyc-prod"  # Or your environment name

# Start the data loading job
az containerapp job start \
  --name $JOB_NAME \
  --resource-group $RG_NAME
```

**Step 4: Monitor Progress**
```bash
# Watch execution status
az containerapp job execution list \
  --name $JOB_NAME \
  --resource-group $RG_NAME \
  --output table

# View logs (get execution name from above)
az containerapp job logs show \
  --name $JOB_NAME \
  --resource-group $RG_NAME \
  --execution {execution-name}
```

**Expected Timeline:**
- File upload: 10-60 minutes (depending on upload method and connection speed)
- Data loading: 60-90 minutes (automatic with duplicate prevention)
- **Total: ~2 hours for complete setup**

**Why This is Fast:**
- Container runs in Azure (same region as database)
- Network latency: <1ms vs 50-100ms from local machine
- 4 CPUs + 8GB RAM + 3 parallel workers
- **10-20x faster than loading from local machine**

### 6. Verify Deployment

```bash
# Check Container App status
az containerapp show \
  --name nyc-prod-backend \
  --resource-group rg-nyc-prod \
  --query "properties.latestRevisionFqdn" -o tsv

# Test health endpoint
curl https://{backend-url}/health
```

---

## API Endpoints

### Trip Data
- **GET** `/api/trips` - Paginated trip data with zone enrichment
  - Query params: `skip`, `limit`, `start_date`, `end_date`, `trip_type`
  - Returns: Trip records with pickup/dropoff borough and zone names

### Aggregates
- **GET** `/api/aggregates/daily` - Daily trip aggregates by type
  - Query params: `start_date`, `end_date`, `trip_type`, `limit`
  - Returns: Daily statistics (total_trips, total_revenue, avg_distance, avg_duration)
  
- **GET** `/api/aggregates/summary` - Summary statistics across date range
  - Query params: `start_date`, `end_date`, `trip_type`
  - Returns: Aggregated totals and averages

### Reference Data
- **GET** `/api/zones` - All taxi zones with borough and service zone info
  - Returns: 265 NYC taxi zones

### Health Check
- **GET** `/health` - Database connectivity and record counts
  - Returns: Connection status and table statistics

### Security
- **Rate Limiting**: 100 req/min for data endpoints, 200 req/min for health checks
- **CORS Protection**: Automatic allowlist for Azure Container Apps + configurable origins
- See [SECURITY.md](docs/SECURITY.md) for comprehensive security documentation

**Full API documentation**: See [API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md)

## Database Schema

The application processes NYC TLC (Taxi & Limousine Commission) trip data with the following architecture:

### Raw Trip Tables
- **yellow_trips** - Yellow taxi trip records (vendor_id, pickup/dropoff times, fare details, payment info)
- **green_trips** - Green taxi trip records (similar schema to yellow)
- **fhv_trips** - For-Hire Vehicle trip records (dispatching base, pickup/dropoff times)
- **fhvhv_trips** - High-Volume FHV records (Uber, Lyft with detailed fare breakdown)
- **taxi_zone_lookup** - Geographic reference (265 zones with borough, zone name, service zone)

### Materialized Views (Pre-computed for Performance)
- **trip_summary_view** - All trips with zone enrichment via LEFT JOIN
  - Adds: pickup_borough, pickup_zone, pickup_service_zone, dropoff_borough, dropoff_zone, dropoff_service_zone
  
- **daily_trip_aggregates** - Daily statistics by trip type
  - Computed metrics: total_trips, total_revenue, avg_trip_distance, avg_trip_duration
  - Indexed on (trip_date, trip_type) for fast queries
  - Refreshed after bulk data loads

### Timestamps & Auditing
All tables include automatic timestamp tracking:
- `created_at` - Record insertion time (server default: CURRENT_TIMESTAMP)
- `updated_at` - Last modification time (auto-updated on changes)

### Loading Taxi Zone Lookup Data

The taxi zone lookup table provides geographic information for each LocationID used in trip records.

**Load zone lookup data (auto-downloads from NYC TLC):**
```bash
cd backend
export DATABASE_URL="postgresql://user:password@host:5432/nycdb"
python load_zone_lookup.py
```

**Load from local CSV file:**
```bash
python load_zone_lookup.py --csv /path/to/taxi_zone_lookup.csv
```

The zone lookup table enriches trip data by joining on `pu_location_id` and `do_location_id`, adding borough names and zone descriptions.

---

## Data Loading (Critical Performance Information)

### Performance Comparison

| Method | Speed | Time for 235 Files | Use Case | Environment |
|--------|-------|---------------------|----------|-------------|
| `load_data.py` (pandas to_sql) | ~475k records/min | ~10-12 hours | Standard loading | Local |
| `load_data_fast.py` (COPY) | **~1.5-2M records/min** | **~2-3 hours** | Fast local loading | Local |
| `load_data_safe.py` (COPY + tracking) | **~1.5-2M records/min** | **~2-3 hours** | **Duplicate prevention** | Local |
| **Azure Container Loader** | **~5-10M records/min** | **~30-60 min** | **Fastest (recommended)** | ☁️ Azure |

### Azure Container Loader (Fastest - Recommended) ⚡⚡⚡

The Azure Container App job runs **inside Azure's network** for 10-20x faster loading:

#### Why It's Faster
- Runs in Azure West US (same region as database)
- Internal network latency: <1ms (vs 50-100ms from local)
- 4 CPUs + 8GB RAM dedicated to loading
- Parallel processing with 3 workers
- **10-20x faster than local loading!**

#### Prerequisites
- Azure infrastructure deployed (see [Azure Deployment](#azure-deployment))
- Storage account and container app job created (automated in Bicep)
- 235 parquet files downloaded locally

#### Setup Process

**1. Download Trip Data (One-Time)**
```bash
cd tlc
./download_tlc_data.sh
```

**2. Upload Files to Azure Blob Storage**

The storage account `nycdevdata` is created automatically by Bicep. Upload files using:

**Option A: Azure CLI (Fastest for automation)**
```bash
# Get connection string from deployment output or Key Vault
export AZURE_STORAGE_CONNECTION_STRING="<from-keyvault>"

# Upload all parquet files
cd tlc
for file in *.parquet; do
  echo "Uploading $file..."
  az storage blob upload \
    --account-name nycdevdata \
    --container-name tlc-data \
    --name "$file" \
    --file "$file" \
    --overwrite
done

# Upload taxi zone lookup
az storage blob upload \
  --account-name nycdevdata \
  --container-name tlc-data \
  --name taxi_zone_lookup.csv \
  --file taxi_zone_lookup.csv \
  --overwrite
```

**Option B: Azure Storage Explorer (GUI - Recommended for first time)**
1. Download: https://azure.microsoft.com/features/storage-explorer/
2. Sign in with your Azure account
3. Navigate to: **nycdevdata → Blob Containers → tlc-data**
4. Click **Upload** → Select all 235 parquet files + taxi_zone_lookup.csv
5. Parallel upload takes ~10-15 minutes

**3. Start the Data Loading Job**
```bash
# Start the container app job
az containerapp job start \
  --name nyc-data-loader-job \
  --resource-group rg-nyc-prod

# Monitor progress
az containerapp job execution list \
  --name nyc-data-loader-job \
  --resource-group rg-nyc-prod \
  --output table

# View logs (replace <execution-name> from above)
az containerapp job logs show \
  --name nyc-data-loader-job \
  --resource-group rg-nyc-prod \
  --execution <execution-name> \
  --container nyc-data-loader-job \
  --tail 100
```

**4. Monitor Loading Progress**
```bash
# Check database stats from local machine
cd backend
export DATABASE_URL="postgresql://nycadmin:{password}@{server}.postgres.database.azure.com:5432/nycdb?sslmode=require"
python3 load_data_safe.py --stats-only
```

**Expected Timeline:**
- Yellow trips (59 files): ~15-20 min
- Green trips (59 files): ~10-15 min  
- FHV trips (59 files): ~20-25 min
- FHVHV trips (58 files): ~25-30 min
- **Total: ~60-90 minutes** vs 3-4 hours locally!

**Duplicate Prevention:**
- The loader tracks files in `loaded_files` table
- Automatically skips already-loaded files
- Safe to restart if job fails
- Won't reload existing data

See [AZURE_LOADER_SETUP.md](backend/AZURE_LOADER_SETUP.md) for detailed troubleshooting and monitoring.

---

### Local Fast Loading (Alternative) ⚡

If you prefer to load from your local machine, use the fast COPY-based loader:

### Local Fast Loading (Alternative) ⚡

If you prefer to load from your local machine, use the fast COPY-based loader with duplicate prevention:

#### 1. Download Trip Data
```bash
cd tlc
./download_tlc_data.sh
```

This downloads parquet files from NYC TLC. Modify the script for specific years or trip types.

#### 2. Initialize Database Schema
```bash
cd backend
export DATABASE_URL="postgresql://user:password@host:5432/nycdb?sslmode=require"
python create_schema.py
```

#### 3. Load Data with Safe Loader (Duplicate Prevention)
```bash
cd backend
export DATABASE_URL="postgresql://user:password@host:5432/nycdb?sslmode=require"

# Run in background for long-running loads
nohup python3 load_data_safe.py --data-dir ../tlc > load_safe.log 2>&1 &
```

**Monitor progress:**
```bash
# Check if process is running
ps aux | grep "load_data_safe.py" | grep -v grep

# View live statistics
python3 load_data_safe.py --stats-only

# Show which files have been loaded
python3 load_data_safe.py --show-loaded

# Watch log file
tail -f load_safe.log
```

**Selective loading:**
```bash
# Load specific trip types
python3 load_data_safe.py --trip-types yellow green

# Specify custom data directory
python3 load_data_safe.py --data-dir /path/to/data
```

**Duplicate Prevention Features:**
- Tracks loaded files in `loaded_files` database table
- Automatically skips files already processed
- Won't reload taxi zones if 265 already exist
- Safe to restart after interruption
- Can run simultaneously with Azure loader (shared tracking table)

#### 4. Post-Load Verification
```bash
# View statistics
python3 load_data_safe.py --stats-only

# Show loaded files
python3 load_data_safe.py --show-loaded

# Output example:
# Current Database Statistics:
# ============================================================
#   yellow_trips        :      50,000,000 records
#   green_trips         :      15,000,000 records
#   fhv_trips           :      25,000,000 records
#   fhvhv_trips         :      40,000,000 records
#   taxi_zone_lookup    :             265 zones
# ------------------------------------------------------------
#   TOTAL TRIPS         :     130,000,000 records
# ============================================================
#
# LOADED FILES TRACKING
# ============================================================
#   yellow    : 59 files,      50,000,000 records
#   green     : 59 files,      15,000,000 records
#   fhv       : 59 files,      25,000,000 records
#   fhvhv     : 58 files,      40,000,000 records
# ------------------------------------------------------------
#   TOTAL     : 235 files,    130,000,000 records
# ============================================================
```

### Legacy Loader (Slowest - Not Recommended)

The original pandas-based loader is kept for compatibility but is much slower:

```bash
cd backend
python load_data.py --data-dir ../tlc
```

### Legacy Loader (Slowest - Not Recommended)

The original pandas-based loader is kept for compatibility but is much slower:

```bash
cd backend
python load_data.py --data-dir ../tlc
```

**Note:** This is 3-5x slower than `load_data_safe.py` and has no duplicate prevention.

### Data Loading Best Practices

**Recommended Approach:**
1. **Production/First-time load**: Use Azure Container Loader (60-90 min)
2. **Development/Testing**: Use `load_data_safe.py` locally (2-3 hours)
3. **Avoid**: `load_data.py` and `load_data_fast.py` (no duplicate tracking)

**Why Use Azure Container Loader?**
- ✅ 10-20x faster (in-region network)
- ✅ Duplicate prevention built-in
- ✅ Automatic progress tracking
- ✅ Can restart without data loss
- ✅ Doesn't tie up your local machine
- ✅ Same cost whether it runs 1 hour or 4 hours

**When to Use Local Loader?**
- Development/testing with small datasets
- You don't have Azure infrastructure yet
- You want to verify data before cloud upload
- Loading to local PostgreSQL for development

### Loading to Azure Database

For Azure PostgreSQL Flexible Server:

```bash
# Set connection string with SSL
export DATABASE_URL="postgresql://nycadmin:PASSWORD@SERVER.postgres.database.azure.com:5432/nycdb?sslmode=require"

# Run fast loader
nohup python3 load_data_fast.py --data-dir ../tlc > azure_load.log 2>&1 &
```

**Important Notes:**
- The COPY loader automatically handles duplicates by continuing on constraint violations
- Materialized views are refreshed automatically after all files load
- Both loaders process files sequentially: yellow → green → fhv → fhvhv
- Loading 235 files with ~130M total records takes 2-3 hours with fast loader

## 🔌 Connecting to Azure Database

### Using pgAdmin

Connection details:
```
Host: {server-name}.postgres.database.azure.com
Port: 5432
Database: nycdb
Username: nycadmin
Password: [retrieve from Key Vault]
SSL Mode: Require
```

### Retrieve Password from Key Vault

```bash
az keyvault secret show \
  --vault-name {vault-name} \
  --name db-password \
  --query "value" -o tsv
```

### Add Firewall Rule

To connect from your local machine:

```bash
# Get your public IP
MY_IP=$(curl -s ifconfig.me)

# Add firewall rule
az postgres flexible-server firewall-rule create \
  --resource-group rg-nyc-prod \
  --name {server-name} \
  --rule-name AllowMyIP \
  --start-ip-address $MY_IP \
  --end-ip-address $MY_IP
```

---

## Tech Stack Details

### Backend
- **FastAPI 0.109** - Modern async web framework
- **SQLAlchemy 2.0** - ORM for database operations
- **Pydantic 2.5** - Data validation and serialization
- **Psycopg2** - PostgreSQL adapter with COPY command support
- **Pandas 2.2** - Data manipulation and parquet processing
- **PyArrow 15.0** - High-performance parquet file reading
- **Uvicorn** - ASGI server for production

### Frontend
- **Angular 17** - Modern framework with standalone components
- **Chart.js 4.5** - Time-series visualizations
- **TypeScript** - Type-safe development
- **RxJS** - Reactive programming for API calls

### Database
- **PostgreSQL 16** - Advanced relational database
- **Materialized Views** - Pre-computed aggregations
- **COPY Command** - High-performance bulk loading
- **Indexes** - B-tree indexes on dates, locations, and composite keys

### DevOps
- **Docker** - Containerization
- **GitHub Actions** - CI/CD pipelines
- **Azure Bicep** - Infrastructure as Code
- **Azure Container Apps** - Serverless container hosting

---

## 🚦 Common Tasks

### Check Backend Status
```bash
curl http://localhost:8000/health
```

### View API Documentation
Open browser to: http://localhost:8000/docs

### Refresh Materialized Views Manually
```bash
psql "$DATABASE_URL" -c "REFRESH MATERIALIZED VIEW CONCURRENTLY trip_summary_view;"
psql "$DATABASE_URL" -c "REFRESH MATERIALIZED VIEW CONCURRENTLY daily_trip_aggregates;"
```

### Kill Background Data Loader
```bash
pkill -f load_data_fast.py
# or
pkill -f load_data.py
```

### View Recent Trips
```bash
psql "$DATABASE_URL" -c "
  SELECT trip_type, pickup_time, fare_amount 
  FROM trip_summary_view 
  ORDER BY pickup_time DESC 
  LIMIT 10;
"
```

### Check Materialized View Stats
```bash
psql "$DATABASE_URL" -c "
  SELECT schemaname, matviewname, last_refresh 
  FROM pg_matviews 
  WHERE schemaname = 'public';
"
```

---

## 🐛 Troubleshooting

### Backend Won't Start
- Check DATABASE_URL is set correctly
- Verify PostgreSQL is running and accessible
- Check firewall rules for Azure PostgreSQL
- Ensure schema is initialized: `python create_schema.py`

### Frontend Can't Connect to Backend
- Check CORS settings in `main.py`
- Verify API URL in `environment.ts`
- Check backend is running: `curl http://localhost:8000/health`

### Data Loading is Slow
- **Use Azure Container Loader** for fastest loading (60-90 min)
- Local: Use `load_data_safe.py` instead of `load_data.py` (3-5x faster)
- Check network bandwidth to Azure (if loading from local)
- Verify no other heavy queries are running
- Azure container runs in same region as database (<1ms latency)

### Materialized Views Out of Date
- Refresh manually after loading data:
  ```bash
  python create_schema.py  # Re-runs refresh
  ```
- Or use PostgreSQL directly:
  ```bash
  psql "$DATABASE_URL" -c "REFRESH MATERIALIZED VIEW CONCURRENTLY daily_trip_aggregates;"
  ```

---

## Performance Benchmarks

### Performance Benchmarks

### Data Loading Performance (Updated with Azure Container)
- **Azure Container Loader**: ~5-10M records/min (60-90 min total) ⚡ **RECOMMENDED**
- **Local Safe Loader** (`load_data_safe.py`): ~1.5-2M records/min (2-3 hours)
- **Local Fast Loader** (`load_data_fast.py`): ~1.5-2M records/min (2-3 hours, no dup prevention)
- **Legacy Loader** (`load_data.py`): ~475k records/min (10-12 hours)
- **Total dataset**: 235 parquet files, ~130M records

### Why Azure Container is Faster
- Runs in Azure West US (same region as database)
- Network latency: <1ms vs 50-100ms from local
- Dedicated 4 CPUs + 8GB RAM
- Parallel processing with 3 workers
- **10-20x faster than local loading!**

### API Response Times (typical)
- `/health`: <50ms
- `/api/zones`: <100ms
- `/api/aggregates/daily` (30 days): <200ms
- `/api/aggregates/summary`: <300ms
- `/api/trips` (paginated, 100 records): <500ms

### Database Metrics
- **trip_summary_view**: ~130M rows (combines all trip types)
- **daily_trip_aggregates**: ~20k rows (one per day per trip type)
- **Indexes**: 15+ indexes across all tables
- **Storage**: ~50GB for full dataset

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests (if applicable)
5. Commit your changes: `git commit -am 'Add new feature'`
6. Push to the branch: `git push origin feature/my-feature`
7. Submit a pull request to `develop` branch

### Coding Standards
- **Backend**: Follow PEP 8 (Python style guide)
- **Frontend**: Follow Angular style guide
- **Commits**: Use conventional commit messages

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

---

## Additional Resources

- [NYC TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) - Official data source
- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Backend framework
- [Angular Documentation](https://angular.io/docs) - Frontend framework
- [PostgreSQL COPY Command](https://www.postgresql.org/docs/current/sql-copy.html) - Bulk loading reference
- [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/) - Hosting documentation

---

## 👥 Authors

**TeckUnlimited** - [teckunlimited](https://github.com/teckunlimited)

---

## 🙏 Acknowledgments

- NYC Taxi & Limousine Commission for providing open data
- FastAPI and SQLAlchemy communities
- Angular and Chart.js teams
