# NYC Project

Full-stack application with FastAPI backend, Angular frontend, and PostgreSQL database deployed on Azure.

## Architecture

- **Backend**: FastAPI (Python)
- **Frontend**: Angular 17
- **Database**: PostgreSQL 16
- **Container Registry**: Azure Container Registry
- **Hosting**: Azure App Service
- **CI/CD**: GitHub Actions

## Project Structure

```
nyc/
├── backend/           # FastAPI backend
├── frontend/          # Angular frontend
├── infra/            # Azure Bicep infrastructure
├── .github/          # GitHub Actions workflows
└── docker-compose.yml
```

## Local Development

### Prerequisites

- Docker and Docker Compose
- Node.js 20+
- Python 3.11+

### Running with Docker Compose

```bash
docker-compose up -d
```

Services will be available at:
- Frontend: http://localhost
- Backend API: http://localhost:8000
- Backend API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432

### Backend Development

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm start
```

## Azure Deployment

### 1. Deploy Infrastructure

```bash
cd infra
az deployment sub create \
  --location eastus \
  --template-file main.bicep \
  --parameters environmentName=nyc
```

### 2. Configure GitHub Secrets

Add the following secrets to your GitHub repository:

- `AZURE_CREDENTIALS`: Azure service principal credentials
- `ACR_LOGIN_SERVER`: Azure Container Registry login server
- `ACR_USERNAME`: ACR username
- `ACR_PASSWORD`: ACR password

### 3. Deploy Application

Push to the `main` branch to trigger automatic deployment.

## Environment Variables

### Backend (.env)

```
DATABASE_URL=postgresql://user:password@host:5432/nycdb
PORT=8000
```

### Frontend

Update `src/environments/environment.ts` with production API URL.

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/items` - Get items

## Database Schema

The application uses NYC TLC (Taxi & Limousine Commission) trip data with the following tables:

- **yellow_trips** - Yellow taxi trip records
- **green_trips** - Green taxi trip records
- **fhv_trips** - For-Hire Vehicle trip records
- **fhvhv_trips** - High-Volume For-Hire Vehicle trip records (Uber, Lyft, etc.)
- **taxi_zone_lookup** - Zone lookup table for enriching trip data with borough and zone names
- **trip_summary_view** - Materialized view for cross-trip analytics

### Loading Taxi Zone Lookup Data

The taxi zone lookup table provides geographic information (borough, zone name, service zone) for each LocationID used in trip records.

**Load zone lookup data:**
```bash
cd backend
export DATABASE_URL="postgresql://user:password@host:5432/nycdb"
python load_zone_lookup.py
```

**Load from local CSV file:**
```bash
python load_zone_lookup.py --csv /path/to/taxi_zone_lookup.csv
```

The script automatically downloads the official zone lookup data from NYC TLC. The zone lookup table is used to enrich trip data by joining on `pu_location_id` and `do_location_id`.

### Loading TLC Trip Data

#### 1. Download Trip Data
Download NYC TLC trip data parquet files:

```bash
cd tlc
./download_tlc_data.sh
```

This script downloads trip data from the NYC TLC website. You can modify the script to select specific years or trip types.

#### 2. Install Dependencies

Ensure you have the required Python packages:

```bash
cd backend
pip install -r requirements.txt
pip install pyarrow  # Required for parquet file support
```

#### 3. Initialize Database Schema

The schema is automatically created when the backend starts. Alternatively, run manually:

```bash
cd backend
python create_schema.py
```

#### 4. Load Data into Database

**Load all available data:**
```bash
cd backend
export DATABASE_URL="postgresql://user:password@host:5432/nycdb"
python load_data.py --data-dir ../tlc
```

**Load specific year:**
```bash
python load_data.py --data-dir ../tlc --year 2024
```

**Load specific trip types:**
```bash
python load_data.py --data-dir ../tlc --trip-types yellow green
```

**View database statistics only:**
```bash
python load_data.py --stats-only
```

#### 5. Loading Data to Azure Database

To load data into your Azure PostgreSQL database:

```bash
cd backend
export DATABASE_URL="postgresql://nycadmin:PASSWORD@SERVER.postgres.database.azure.com:5432/nycdb?sslmode=require"
python load_data.py --data-dir ../tlc
```

**Important Notes:**
- The loader automatically handles duplicate data - you can safely run it multiple times
- Loading large datasets takes time (235 files can take several hours)
- Data is loaded in batches of 50,000 records for optimal performance
- Run in background: `nohup python3 load_data.py --data-dir ../tlc > load_all.log 2>&1 &`

#### 6. Monitor Loading Progress

**Check if loading process is running:**
```bash
ps aux | grep "load_data.py" | grep -v grep
```

**View current record counts:**
```bash
psql "$DATABASE_URL" -c "
  SELECT 'yellow_trips' as table, COUNT(*) as records FROM yellow_trips
  UNION ALL SELECT 'green_trips', COUNT(*) FROM green_trips
  UNION ALL SELECT 'fhv_trips', COUNT(*) FROM fhv_trips
  UNION ALL SELECT 'fhvhv_trips', COUNT(*) FROM fhvhv_trips
  ORDER BY table;
"
```

**View record counts with date ranges:**
```bash
psql "$DATABASE_URL" -c "
  SELECT 'yellow_trips' as table, COUNT(*) as records, 
         MIN(tpep_pickup_datetime)::date as earliest, 
         MAX(tpep_pickup_datetime)::date as latest 
  FROM yellow_trips
  UNION ALL 
  SELECT 'green_trips', COUNT(*), 
         MIN(lpep_pickup_datetime)::date, 
         MAX(lpep_pickup_datetime)::date 
  FROM green_trips
  ORDER BY table;
"
```

**Check process status:**
```bash
# Find the process ID
pgrep -f load_data.py

# View process details
ps aux | grep [p]ython | grep load_data
```

#### Connecting to Azure Database

Use pgAdmin or any PostgreSQL client with these connection details:

```
Host: YOUR-SERVER.postgres.database.azure.com
Port: 5432
Database: nycdb
Username: nycadmin
Password: [from Azure Key Vault secret: db-password]
SSL Mode: Require
```

Retrieve the password from Azure Key Vault:
```bash
az keyvault secret show --vault-name YOUR-VAULT --name db-password --query "value" -o tsv
```

## Contributing

1. Create a feature branch
2. Make your changes
3. Submit a pull request

## License

MIT
