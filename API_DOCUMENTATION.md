# NYC TLC Trip Data API Documentation

## Overview
RESTful API for accessing NYC Taxi & Limousine Commission trip data with built-in analytics and aggregations.

## Base URL
- **Local Development**: `http://localhost:8000`
- **Azure Production**: `https://nyc-dev-backend.azurecontainerapps.io`

## Authentication
No authentication required - all endpoints are publicly accessible.

---

## Core Endpoints

### Health Check
**GET** `/health`

Check API status and database connectivity.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "environment": "local",
  "trip_counts": {
    "yellow_trips": 8637817,
    "green_trips": 0,
    "fhv_trips": 0,
    "fhvhv_trips": 0
  }
}
```

---

## Daily Aggregates API

### Get Daily Aggregates
**GET** `/api/aggregates/daily`

Retrieve daily aggregated trip statistics.

**Query Parameters:**
- `start_date` (optional): Start date in YYYY-MM-DD format
- `end_date` (optional): End date in YYYY-MM-DD format
- `trip_type` (optional): Filter by type - `yellow`, `green`, `fhv`, `fhvhv`
- `limit` (optional): Max records to return (1-1000, default: 100)

**Response:**
```json
{
  "total": 100,
  "data": [
    {
      "trip_date": "2021-07-19",
      "trip_type": "yellow",
      "total_trips": 65356,
      "total_revenue": 1146696.88,
      "avg_trip_distance": 2.76,
      "avg_trip_duration": 14.61,
      "avg_fare_amount": 12.45,
      "avg_tip_amount": 2.34,
      "total_passengers": 98034,
      "avg_passengers": 1.5
    }
  ]
}
```

### Get Aggregates Summary
**GET** `/api/aggregates/summary`

Get summary statistics across all trip types for a date range.

**Query Parameters:**
- `start_date` (optional): Start date in YYYY-MM-DD format
- `end_date` (optional): End date in YYYY-MM-DD format

**Response:**
```json
{
  "summary": [
    {
      "trip_type": "yellow",
      "days": 30,
      "total_trips": 1500000,
      "total_revenue": 25000000.50,
      "avg_distance": 2.85,
      "avg_duration": 15.2
    }
  ]
}
```

---

## Trip Data API

### Get Trips (Paginated)
**GET** `/api/trips`

Retrieve individual trip records with enriched zone information.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (1-100, default: 50)
- `trip_type` (optional): Filter by type - `yellow`, `green`, `fhv`, `fhvhv`
- `start_date` (optional): Filter trips from this date (YYYY-MM-DD)
- `end_date` (optional): Filter trips until this date (YYYY-MM-DD)

**Response:**
```json
{
  "total": 8637817,
  "page": 1,
  "page_size": 50,
  "total_pages": 172757,
  "data": [
    {
      "id": 12345,
      "trip_type": "yellow",
      "pickup_datetime": "2021-07-19T14:30:00",
      "dropoff_datetime": "2021-07-19T14:45:00",
      "pu_location_id": 161,
      "pickup_borough": "Manhattan",
      "pickup_zone": "Midtown Center",
      "do_location_id": 236,
      "dropoff_borough": "Manhattan",
      "dropoff_zone": "Upper East Side South",
      "trip_distance": 2.5,
      "fare_amount": 12.50,
      "tip_amount": 2.50,
      "total_amount": 18.30,
      "duration_minutes": 15.0
    }
  ]
}
```

---

## Zone Lookup API

### Get All Zones
**GET** `/api/zones`

Retrieve all taxi zone lookup data.

**Response:**
```json
{
  "total": 265,
  "zones": [
    {
      "location_id": 1,
      "borough": "Manhattan",
      "zone": "Midtown Center",
      "service_zone": "Yellow Zone"
    }
  ]
}
```

---

## Data Models

### Daily Aggregate
- `trip_date` (date): Date of aggregation
- `trip_type` (string): Type of trip (yellow, green, fhv, fhvhv)
- `total_trips` (integer): Total number of trips
- `total_revenue` (float): Total revenue in dollars
- `avg_trip_distance` (float): Average trip distance in miles
- `avg_trip_duration` (float): Average trip duration in minutes
- `avg_fare_amount` (float): Average fare amount
- `avg_tip_amount` (float): Average tip amount
- `total_passengers` (float): Total passenger count
- `avg_passengers` (float): Average passengers per trip

### Trip
- `id` (integer): Unique trip identifier
- `trip_type` (string): Type of trip
- `pickup_datetime` (datetime): Pickup timestamp
- `dropoff_datetime` (datetime): Dropoff timestamp
- `pu_location_id` (integer): Pickup location ID
- `pickup_borough` (string): Pickup borough name
- `pickup_zone` (string): Pickup zone name
- `do_location_id` (integer): Dropoff location ID
- `dropoff_borough` (string): Dropoff borough name
- `dropoff_zone` (string): Dropoff zone name
- `trip_distance` (float): Distance in miles
- `fare_amount` (float): Base fare
- `tip_amount` (float): Tip amount
- `total_amount` (float): Total amount charged
- `duration_minutes` (float): Trip duration in minutes

---

## Database Schema

### Raw Trip Tables
- `yellow_trips`: Yellow taxi trip records
- `green_trips`: Green taxi trip records
- `fhv_trips`: For-hire vehicle trip records
- `fhvhv_trips`: High-volume for-hire vehicle trip records
- `taxi_zone_lookup`: Zone ID to name mapping

### Analytics Views
- `trip_summary_view`: Unified view of all trips with zone enrichment
- `daily_trip_aggregates`: Pre-computed daily statistics (materialized view)

---

## Performance Notes

1. **Materialized Views**: Daily aggregates are pre-computed and need periodic refresh
2. **Pagination**: Always use pagination for large datasets
3. **Date Filters**: Use date filters to limit result sets
4. **Indexes**: Optimized for date-based queries and location lookups

---

## Example Usage

### Get last 30 days of yellow taxi aggregates
```bash
curl "http://localhost:8000/api/aggregates/daily?trip_type=yellow&limit=30"
```

### Get trips for a specific date range
```bash
curl "http://localhost:8000/api/trips?start_date=2021-07-01&end_date=2021-07-31&page_size=100"
```

### Get summary for current month
```bash
curl "http://localhost:8000/api/aggregates/summary?start_date=2021-07-01&end_date=2021-07-31"
```

---

## Error Responses

All error responses follow this format:
```json
{
  "detail": "Error message description"
}
```

**Common HTTP Status Codes:**
- `200 OK`: Successful request
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error
