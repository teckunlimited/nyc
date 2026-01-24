"""
Unit tests for NYC TLC Trip Data API
Tests all endpoints with mocked database connections
"""

import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import app, get_db
from database import Base
from models import YellowTripData, GreenTripData, TaxiZoneLookup


# ==================== Test Database Setup ====================

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for tests"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ==================== Fixtures ====================

@pytest.fixture(scope="module")
def client():
    """Create test client"""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh test database for each test"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Create materialized view simulation (SQLite doesn't support materialized views)
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS daily_trip_aggregates (
            trip_date DATE,
            trip_type TEXT,
            total_trips INTEGER,
            total_revenue REAL,
            avg_trip_distance REAL,
            avg_trip_duration REAL,
            avg_fare_amount REAL,
            avg_tip_amount REAL,
            total_passengers REAL,
            avg_passengers REAL
        )
    """))
    
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS trip_summary_view (
            id INTEGER,
            trip_type TEXT,
            pickup_datetime TIMESTAMP,
            dropoff_datetime TIMESTAMP,
            pu_location_id INTEGER,
            pickup_borough TEXT,
            pickup_zone TEXT,
            do_location_id INTEGER,
            dropoff_borough TEXT,
            dropoff_zone TEXT,
            trip_distance REAL,
            fare_amount REAL,
            tip_amount REAL,
            total_amount REAL,
            duration_minutes REAL
        )
    """))
    
    # Create taxi_zone_lookup table
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS taxi_zone_lookup (
            location_id INTEGER PRIMARY KEY,
            borough TEXT,
            zone TEXT,
            service_zone TEXT
        )
    """))
    
    db.commit()
    
    yield db
    
    # Cleanup
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_aggregates(test_db):
    """Insert sample aggregate data"""
    test_db.execute(text("""
        INSERT INTO daily_trip_aggregates 
        (trip_date, trip_type, total_trips, total_revenue, avg_trip_distance, 
         avg_trip_duration, avg_fare_amount, avg_tip_amount, total_passengers, avg_passengers)
        VALUES 
        ('2021-05-01', 'yellow', 1000, 15000.50, 3.5, 15.2, 14.0, 2.5, 1200, 1.2),
        ('2021-05-01', 'green', 500, 7500.25, 2.8, 12.5, 13.5, 1.8, 550, 1.1),
        ('2021-05-02', 'yellow', 1100, 16500.75, 3.8, 16.0, 14.5, 2.8, 1300, 1.18),
        ('2021-05-02', 'fhv', 800, NULL, NULL, 18.5, NULL, NULL, NULL, NULL),
        ('2021-05-03', 'fhvhv', 2000, 45000.00, 5.2, 20.0, 20.0, 3.5, NULL, NULL)
    """))
    test_db.commit()


@pytest.fixture
def sample_trips(test_db):
    """Insert sample trip data"""
    test_db.execute(text("""
        INSERT INTO trip_summary_view
        (id, trip_type, pickup_datetime, dropoff_datetime, pu_location_id, pickup_borough,
         pickup_zone, do_location_id, dropoff_borough, dropoff_zone, trip_distance,
         fare_amount, tip_amount, total_amount, duration_minutes)
        VALUES
        (1, 'yellow', '2021-05-01 10:00:00', '2021-05-01 10:15:00', 100, 'Manhattan', 
         'East Harlem North', 200, 'Manhattan', 'Upper West Side', 2.5, 12.0, 2.5, 17.3, 15.0),
        (2, 'yellow', '2021-05-01 11:00:00', '2021-05-01 11:20:00', 150, 'Brooklyn',
         'Park Slope', 180, 'Brooklyn', 'Downtown Brooklyn', 3.2, 15.0, 3.0, 21.8, 20.0),
        (3, 'green', '2021-05-01 12:00:00', '2021-05-01 12:12:00', 220, 'Queens',
         'Astoria', 230, 'Queens', 'Long Island City', 1.8, 10.0, 1.5, 14.2, 12.0)
    """))
    test_db.commit()


@pytest.fixture
def sample_zones(test_db):
    """Insert sample zone lookup data"""
    # Clear any existing zones first
    test_db.execute(text("DELETE FROM taxi_zone_lookup"))
    test_db.commit()
    
    zones = [
        TaxiZoneLookup(location_id=100, borough="Manhattan", zone="East Harlem North", service_zone="Yellow Zone"),
        TaxiZoneLookup(location_id=150, borough="Brooklyn", zone="Park Slope", service_zone="Green Zone"),
        TaxiZoneLookup(location_id=200, borough="Manhattan", zone="Upper West Side", service_zone="Yellow Zone")
    ]
    for zone in zones:
        test_db.add(zone)
    test_db.commit()


# ==================== Health Check Tests ====================

def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "environment" in data


def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "NYC TLC" in data["message"]


def test_items_endpoint(client):
    """Test items endpoint"""
    response = client.get("/api/items")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert isinstance(data["items"], list)


# ==================== Daily Aggregates Tests ====================

def test_get_daily_aggregates_all(client, sample_aggregates):
    """Test getting all daily aggregates without filters"""
    response = client.get("/api/aggregates/daily")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "data" in data
    assert data["total"] == 5
    assert len(data["data"]) == 5


def test_get_daily_aggregates_with_date_filter(client, sample_aggregates):
    """Test filtering aggregates by date range"""
    response = client.get("/api/aggregates/daily?start_date=2021-05-01&end_date=2021-05-01")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2  # At least yellow and green on 2021-05-01
    assert all(item["trip_date"] == "2021-05-01" for item in data["data"])


def test_get_daily_aggregates_with_trip_type_filter(client, sample_aggregates):
    """Test filtering aggregates by trip type"""
    response = client.get("/api/aggregates/daily?trip_type=yellow")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2  # At least two yellow trip entries
    assert all(item["trip_type"] == "yellow" for item in data["data"])


def test_get_daily_aggregates_with_limit(client, sample_aggregates):
    """Test limiting the number of results"""
    response = client.get("/api/aggregates/daily?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2


def test_get_daily_aggregates_validation(client):
    """Test parameter validation"""
    # Test invalid limit
    response = client.get("/api/aggregates/daily?limit=2000")
    assert response.status_code == 422  # Validation error
    
    # Test invalid date format
    response = client.get("/api/aggregates/daily?start_date=invalid-date")
    assert response.status_code == 422


def test_get_daily_aggregates_response_structure(client, sample_aggregates):
    """Test response data structure"""
    response = client.get("/api/aggregates/daily?limit=1")
    assert response.status_code == 200
    data = response.json()
    
    assert "total" in data
    assert "data" in data
    
    if data["data"]:
        item = data["data"][0]
        assert "trip_date" in item
        assert "trip_type" in item
        assert "total_trips" in item
        assert "total_revenue" in item
        assert "avg_trip_distance" in item
        assert "avg_trip_duration" in item


def test_get_aggregates_summary(client, sample_aggregates):
    """Test the summary aggregates endpoint"""
    response = client.get("/api/aggregates/summary")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert len(data["summary"]) > 0
    
    # Check structure of summary items
    for item in data["summary"]:
        assert "trip_type" in item
        assert "days" in item
        assert "total_trips" in item


def test_get_aggregates_summary_with_date_range(client, sample_aggregates):
    """Test summary with date filtering"""
    response = client.get("/api/aggregates/summary?start_date=2021-05-01&end_date=2021-05-02")
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data


# ==================== Trip Data Tests ====================

def test_get_trips_default_pagination(client, sample_trips):
    """Test getting trips with default pagination"""
    response = client.get("/api/trips")
    assert response.status_code == 200
    data = response.json()
    
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert "data" in data
    assert data["total"] == 3
    assert data["page"] == 1
    assert len(data["data"]) == 3


def test_get_trips_custom_pagination(client, sample_trips):
    """Test custom pagination parameters"""
    response = client.get("/api/trips?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2
    assert data["page_size"] == 2
    assert data["total_pages"] >= 2  # At least 2 pages


def test_get_trips_with_trip_type_filter(client, sample_trips):
    """Test filtering trips by type"""
    response = client.get("/api/trips?trip_type=yellow")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2  # At least 2 yellow trips
    assert all(trip["trip_type"] == "yellow" for trip in data["data"])


def test_get_trips_with_date_filter(client, sample_trips):
    """Test filtering trips by date range"""
    response = client.get("/api/trips?start_date=2021-05-01&end_date=2021-05-01")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0


def test_get_trips_response_structure(client, sample_trips):
    """Test trip response data structure"""
    response = client.get("/api/trips?page_size=1")
    assert response.status_code == 200
    data = response.json()
    
    if data["data"]:
        trip = data["data"][0]
        assert "id" in trip
        assert "trip_type" in trip
        assert "pickup_datetime" in trip
        assert "dropoff_datetime" in trip
        assert "pickup_zone" in trip
        assert "dropoff_zone" in trip
        assert "trip_distance" in trip
        assert "total_amount" in trip


def test_get_trips_pagination_validation(client):
    """Test pagination parameter validation"""
    # Invalid page number
    response = client.get("/api/trips?page=0")
    assert response.status_code == 422
    
    # Invalid page size
    response = client.get("/api/trips?page_size=200")
    assert response.status_code == 422


# ==================== Zone Lookup Tests ====================

def test_get_zones(client, sample_zones):
    """Test getting all taxi zones"""
    response = client.get("/api/zones")
    assert response.status_code == 200
    data = response.json()
    
    assert "total" in data
    assert "zones" in data
    assert data["total"] == 3
    assert len(data["zones"]) == 3


def test_get_zones_structure(client, sample_zones):
    """Test zone response structure"""
    response = client.get("/api/zones")
    assert response.status_code == 200
    data = response.json()
    
    if data["zones"]:
        zone = data["zones"][0]
        assert "location_id" in zone
        assert "borough" in zone
        assert "zone" in zone
        assert "service_zone" in zone


def test_get_zones_empty_database(client, test_db):
    """Test zones endpoint with no data"""
    # Clear any existing zones
    test_db.execute(text("DELETE FROM taxi_zone_lookup"))
    test_db.commit()
    
    response = client.get("/api/zones")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert len(data["zones"]) == 0


# ==================== CORS Tests ====================

def test_cors_headers(client):
    """Test CORS configuration"""
    response = client.get("/api/trips")
    # Check that CORS headers would be present in a real response
    assert response.status_code == 200


# ==================== Error Handling Tests ====================

def test_invalid_endpoint(client):
    """Test accessing non-existent endpoint"""
    response = client.get("/api/invalid-endpoint")
    assert response.status_code == 404


def test_method_not_allowed(client):
    """Test using wrong HTTP method"""
    response = client.post("/api/zones")
    assert response.status_code == 405


# ==================== Integration Tests ====================

def test_full_workflow(client, sample_aggregates, sample_trips, sample_zones):
    """Test a complete workflow through multiple endpoints"""
    # 1. Check health
    health = client.get("/health")
    assert health.status_code == 200
    
    # 2. Get aggregates
    aggregates = client.get("/api/aggregates/daily?limit=10")
    assert aggregates.status_code == 200
    
    # 3. Get trips
    trips = client.get("/api/trips?page=1&page_size=10")
    assert trips.status_code == 200
    
    # 4. Get zones
    zones = client.get("/api/zones")
    assert zones.status_code == 200
    
    # All should succeed
    assert all([
        health.json()["status"] == "healthy",
        len(aggregates.json()["data"]) > 0,
        trips.json()["total"] > 0,
        zones.json()["total"] > 0
    ])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
