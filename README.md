# NYC Taxi Trip Analytics Platform

A production-ready, full-stack analytics platform for NYC TLC (Taxi & Limousine Commission) trip data. Features real-time dashboards, time-series visualizations, and efficient bulk data processing with PostgreSQL materialized views.

## 🎯 Features

- **Real-time Analytics Dashboard** - Interactive charts showing daily trip patterns and revenue trends
- **High-Performance Data Loading** - PostgreSQL COPY command for 3-5x faster bulk imports
- **Materialized Views** - Pre-computed daily aggregates for lightning-fast queries
- **Zone Enrichment** - Trip data enriched with NYC borough and zone information
- **RESTful API** - Comprehensive endpoints with pagination and filtering
- **Time-Series Charts** - Chart.js visualizations with color-coded trip types
- **Date Filtering** - Flexible date range selection and trip type filtering
- **Scalable Architecture** - Deployed on Azure with CI/CD pipelines

## 🏗️ Architecture

- **Backend**: FastAPI (Python 3.11) with SQLAlchemy ORM and Pydantic validation
- **Frontend**: Angular 17 with standalone components and Chart.js 4.5
- **Database**: Azure PostgreSQL 16 Flexible Server with materialized views
- **Container Registry**: Azure Container Registry (ACR)
- **Hosting**: Azure Container Apps (Backend) + Static Web App (Frontend potential)
- **CI/CD**: GitHub Actions for automated deployment
- **Data Format**: Parquet files with pandas/pyarrow processing

## 📁 Project Structure

```
nyc/
├── backend/               # FastAPI backend
│   ├── main.py           # API endpoints and application
│   ├── models.py         # SQLAlchemy ORM models
│   ├── schemas.py        # Pydantic validation schemas
│   ├── database.py       # Database connection
│   ├── create_schema.py  # Schema and view creation
│   ├── load_data.py      # Standard data loader
│   ├── load_data_fast.py # Fast COPY-based loader (3-5x faster)
│   ├── load_zone_lookup.py # Zone lookup data loader
│   └── requirements.txt  # Python dependencies
├── frontend/             # Angular frontend
│   ├── src/
│   │   └── app/
│   │       └── app.component.ts  # Main dashboard component
│   ├── package.json      # Node dependencies
│   └── angular.json      # Angular configuration
├── infra/               # Azure Bicep infrastructure
│   ├── main.bicep       # Main infrastructure template
│   ├── resources.bicep  # Resource definitions
│   └── main.bicepparam  # Parameters
├── tlc/                 # TLC data storage
│   ├── download_tlc_data.sh  # Data download script
│   └── *.parquet        # Trip data files (235 files)
├── .github/
│   └── workflows/       # CI/CD pipelines
└── docker-compose.yml   # Local development setup
```

---

## 🔧 Local Development

### Prerequisites

- Docker and Docker Compose (optional)
- Node.js 20+
- Python 3.11+
- PostgreSQL 16 (or use Azure PostgreSQL)

### Running with Docker Compose

```bash
docker-compose up -d
```

Services will be available at:
- **Frontend**: http://localhost
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Interactive Swagger UI)
- **PostgreSQL**: localhost:5432

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set database connection
export DATABASE_URL="postgresql://user:password@host:5432/nycdb"

# Initialize schema
python create_schema.py

# Start development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Backend will be available at:**
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Frontend Development

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
```

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

## ☁️ Azure Deployment

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
- Key Vault: `nyc-prod-kv{uniqueid}`
- Log Analytics workspace

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

After infrastructure deployment, load trip data:

```bash
cd backend

# Set Azure database connection
export DATABASE_URL="postgresql://nycadmin:{password}@{server}.postgres.database.azure.com:5432/nycdb?sslmode=require"

# Initialize schema
python create_schema.py

# Load zone lookup
python load_zone_lookup.py

# Load trip data (fast method)
nohup python3 load_data_fast.py --data-dir ../tlc > azure_load.log 2>&1 &
```

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

**Full API documentation**: See [API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md)

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

## 🚀 Data Loading (Critical Performance Information)

### Performance Comparison

| Method | Speed | Time for 235 Files | Use Case |
|--------|-------|---------------------|----------|
| `load_data.py` (pandas to_sql) | ~475k records/min | ~10-12 hours | Standard loading |
| `load_data_fast.py` (COPY) | **~1.5-2M records/min** | **~2-3 hours** | **Recommended** |

### Fast Loading (Recommended) ⚡

The fast loader uses PostgreSQL's native COPY command for **3-5x faster** bulk imports:

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

#### 3. Load Data with Fast Loader
```bash
cd backend
export DATABASE_URL="postgresql://user:password@host:5432/nycdb?sslmode=require"

# Run in background for long-running loads
nohup python3 load_data_fast.py --data-dir ../tlc > load_fast.log 2>&1 &
```

**Monitor progress:**
```bash
# Check if process is running
ps aux | grep "load_data_fast.py" | grep -v grep

# View live statistics
python3 load_data_fast.py --stats-only

# Watch log file
tail -f load_fast.log
```

**Selective loading:**
```bash
# Load specific year
python3 load_data_fast.py --data-dir ../tlc --year 2024

# Load specific trip types
python3 load_data_fast.py --data-dir ../tlc --trip-types yellow green
```

#### 4. Post-Load Verification
```bash
# View statistics
python3 load_data_fast.py --stats-only

# Output example:
# Current Database Statistics:
# ------------------------------------------------------------
#   yellow_trips        :      50,000,000 records
#   green_trips         :      15,000,000 records
#   fhv_trips           :      25,000,000 records
#   fhvhv_trips         :      40,000,000 records
# ------------------------------------------------------------
#   TOTAL               :     130,000,000 records
#   Date range: 2009-01-01 to 2024-12-31
```

### Standard Loader (Slower Alternative)

If you prefer the standard pandas-based loader:

```bash
cd backend
python load_data.py --data-dir ../tlc
```

**Note:** This is 3-5x slower but may be more stable on some systems.

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

## 📊 Tech Stack Details

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
- Use `load_data_fast.py` instead of `load_data.py` (3-5x faster)
- Check network bandwidth to Azure (if loading to cloud)
- Verify no other heavy queries are running
- Consider loading in batches by year: `--year 2024`

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

## 📈 Performance Benchmarks

### Data Loading Performance
- **Standard loader** (`load_data.py`): ~475k records/min
- **Fast loader** (`load_data_fast.py`): ~1.5-2M records/min
- **Total dataset**: 235 parquet files, ~130M records
- **Load time (fast)**: 2-3 hours

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

## 📝 Contributing

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

## 🔗 Additional Resources

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
