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

TBD - Add your database models here

## Contributing

1. Create a feature branch
2. Make your changes
3. Submit a pull request

## License

MIT
