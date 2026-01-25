from fastapi import FastAPI, Depends, HTTPException, Query, status, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func, and_, or_
from typing import Optional, List
from datetime import datetime, date, timedelta
import os
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from database import get_db, engine, Base
from models import YellowTripData, GreenTripData, FHVTripData, FHVHVTripData, TaxiZoneLookup
from schemas import (
    TripResponse, DailyAggregateResponse, PaginatedResponse, 
    DailyAggregateListResponse, HealthResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="NYC TLC Trip Data API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def create_schema_on_startup():
    """
    Create all database tables, indexes, and views on startup
    This runs automatically during deployment
    """
    try:
        logger.info("Creating database schema...")
        
        # Create all tables and indexes in a single transaction
        with engine.begin() as conn:
            # Create all tables from models
            Base.metadata.create_all(bind=conn)
            logger.info("✓ Tables created")
            # Skip index creation temporarily to test database connection
            # Check and create indexes only if they don't exist (fast skip for dev, creates for staging)
            logger.info("Checking existing indexes...")
            
            # Check if main performance indexes exist
            indexes_exist = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE tablename = 'yellow_trips' AND indexname = 'idx_yellow_pickup_date'
                )
            """)).scalar()
            
            if not indexes_exist:
                logger.info("Creating performance indexes (tables appear to be new)...")
                
                conn.execute(text("""
                    CREATE INDEX idx_yellow_pickup_date 
                    ON yellow_trips (tpep_pickup_datetime DESC)
                """))
                
                conn.execute(text("""
                    CREATE INDEX idx_green_pickup_date 
                    ON green_trips (lpep_pickup_datetime DESC)
                """))
                
                conn.execute(text("""
                    CREATE INDEX idx_fhv_pickup_date 
                    ON fhv_trips (pickup_datetime DESC)
                """))
                
                conn.execute(text("""
                    CREATE INDEX idx_fhvhv_pickup_date 
                    ON fhvhv_trips (pickup_datetime DESC)
                """))
                
                # Create location indexes
                conn.execute(text("""
                    CREATE INDEX idx_yellow_locations 
                    ON yellow_trips (pu_location_id, do_location_id)
                """))
                
                conn.execute(text("""
                    CREATE INDEX idx_green_locations 
                    ON green_trips (pu_location_id, do_location_id)
                """))
                
                logger.info("✓ Performance indexes created")
            else:
                logger.info("✓ Performance indexes already exist, skipping creation")
            
            # Create materialized views only if they don't exist
            logger.info("Checking for existing materialized views...")
            
            # Check if trip_summary_view exists
            view_exists = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_matviews 
                    WHERE schemaname = 'public' AND matviewname = 'trip_summary_view'
                )
            """)).scalar()
            
            if not view_exists:
                logger.info("Creating trip_summary_view...")
                # Create unified trip summary view with zone enrichment
                conn.execute(text("""
                    CREATE MATERIALIZED VIEW trip_summary_view AS
                SELECT 
                    y.id,
                    'yellow' as trip_type,
                    y.tpep_pickup_datetime as pickup_datetime,
                    y.tpep_dropoff_datetime as dropoff_datetime,
                    y.pu_location_id,
                    pu.borough as pickup_borough,
                    pu.zone as pickup_zone,
                    pu.service_zone as pickup_service_zone,
                    y.do_location_id,
                    do.borough as dropoff_borough,
                    do.zone as dropoff_zone,
                    do.service_zone as dropoff_service_zone,
                    y.trip_distance,
                    y.fare_amount,
                    y.tip_amount,
                    y.total_amount,
                    EXTRACT(EPOCH FROM (y.tpep_dropoff_datetime - y.tpep_pickup_datetime))/60 as duration_minutes
                FROM yellow_trips y
                LEFT JOIN taxi_zone_lookup pu ON y.pu_location_id = pu.location_id
                LEFT JOIN taxi_zone_lookup do ON y.do_location_id = do.location_id
                WHERE y.tpep_pickup_datetime IS NOT NULL AND y.tpep_dropoff_datetime IS NOT NULL
                
                UNION ALL
                
                SELECT 
                    g.id,
                    'green' as trip_type,
                    g.lpep_pickup_datetime as pickup_datetime,
                    g.lpep_dropoff_datetime as dropoff_datetime,
                    g.pu_location_id,
                    pu.borough as pickup_borough,
                    pu.zone as pickup_zone,
                    pu.service_zone as pickup_service_zone,
                    g.do_location_id,
                    do.borough as dropoff_borough,
                    do.zone as dropoff_zone,
                    do.service_zone as dropoff_service_zone,
                    g.trip_distance,
                    g.fare_amount,
                    g.tip_amount,
                    g.total_amount,
                    EXTRACT(EPOCH FROM (g.lpep_dropoff_datetime - g.lpep_pickup_datetime))/60 as duration_minutes
                FROM green_trips g
                LEFT JOIN taxi_zone_lookup pu ON g.pu_location_id = pu.location_id
                LEFT JOIN taxi_zone_lookup do ON g.do_location_id = do.location_id
                WHERE g.lpep_pickup_datetime IS NOT NULL AND g.lpep_dropoff_datetime IS NOT NULL
                
                UNION ALL
                
                SELECT 
                    f.id,
                    'fhv' as trip_type,
                    f.pickup_datetime,
                    f.dropoff_datetime,
                    CAST(f.pu_location_id AS INTEGER) as pu_location_id,
                    pu.borough as pickup_borough,
                    pu.zone as pickup_zone,
                    pu.service_zone as pickup_service_zone,
                    CAST(f.do_location_id AS INTEGER) as do_location_id,
                    do.borough as dropoff_borough,
                    do.zone as dropoff_zone,
                    do.service_zone as dropoff_service_zone,
                    NULL::float as trip_distance,
                    NULL::float as fare_amount,
                    NULL::float as tip_amount,
                    NULL::float as total_amount,
                    EXTRACT(EPOCH FROM (f.dropoff_datetime - f.pickup_datetime))/60 as duration_minutes
                FROM fhv_trips f
                LEFT JOIN taxi_zone_lookup pu ON CAST(f.pu_location_id AS INTEGER) = pu.location_id
                LEFT JOIN taxi_zone_lookup do ON CAST(f.do_location_id AS INTEGER) = do.location_id
                WHERE f.pickup_datetime IS NOT NULL AND f.dropoff_datetime IS NOT NULL
                
                UNION ALL
                
                SELECT 
                    h.id,
                    'fhvhv' as trip_type,
                    h.pickup_datetime,
                    h.dropoff_datetime,
                    h.pu_location_id,
                    pu.borough as pickup_borough,
                    pu.zone as pickup_zone,
                    pu.service_zone as pickup_service_zone,
                    h.do_location_id,
                    do.borough as dropoff_borough,
                    do.zone as dropoff_zone,
                    do.service_zone as dropoff_service_zone,
                    h.trip_miles as trip_distance,
                    h.base_passenger_fare as fare_amount,
                    h.tips as tip_amount,
                    (COALESCE(h.base_passenger_fare, 0) + COALESCE(h.tolls, 0) + 
                     COALESCE(h.bcf, 0) + COALESCE(h.sales_tax, 0) + 
                     COALESCE(h.congestion_surcharge, 0) + COALESCE(h.airport_fee, 0) + 
                     COALESCE(h.tips, 0)) as total_amount,
                    EXTRACT(EPOCH FROM (h.dropoff_datetime - h.pickup_datetime))/60 as duration_minutes
                FROM fhvhv_trips h
                LEFT JOIN taxi_zone_lookup pu ON h.pu_location_id = pu.location_id
                LEFT JOIN taxi_zone_lookup do ON h.do_location_id = do.location_id
                WHERE h.pickup_datetime IS NOT NULL AND h.dropoff_datetime IS NOT NULL
            """))
            
                # Create indexes on materialized view
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_summary_trip_type ON trip_summary_view (trip_type)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_summary_pickup_date ON trip_summary_view (pickup_datetime)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_summary_locations ON trip_summary_view (pu_location_id, do_location_id)
                """))
                
                logger.info("✓ Trip summary view created")
            else:
                logger.info("✓ Trip summary view already exists, skipping creation")
            
            # Check if daily_trip_aggregates exists
            daily_view_exists = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_matviews 
                    WHERE schemaname = 'public' AND matviewname = 'daily_trip_aggregates'
                )
            """)).scalar()
            
            if not daily_view_exists:
                logger.info("Creating daily aggregates view...")
                conn.execute(text("""
                    CREATE MATERIALIZED VIEW daily_trip_aggregates AS
                WITH yellow_daily AS (
                    SELECT 
                        DATE(tpep_pickup_datetime) as trip_date,
                        'yellow' as trip_type,
                        COUNT(*) as total_trips,
                        SUM(total_amount) as total_revenue,
                        AVG(trip_distance) as avg_trip_distance,
                        AVG(EXTRACT(EPOCH FROM (tpep_dropoff_datetime - tpep_pickup_datetime))/60) as avg_trip_duration,
                        AVG(fare_amount) as avg_fare_amount,
                        AVG(tip_amount) as avg_tip_amount,
                        SUM(passenger_count) as total_passengers,
                        AVG(passenger_count) as avg_passengers
                    FROM yellow_trips
                    WHERE tpep_pickup_datetime IS NOT NULL
                    GROUP BY DATE(tpep_pickup_datetime)
                ),
                green_daily AS (
                    SELECT 
                        DATE(lpep_pickup_datetime) as trip_date,
                        'green' as trip_type,
                        COUNT(*) as total_trips,
                        SUM(total_amount) as total_revenue,
                        AVG(trip_distance) as avg_trip_distance,
                        AVG(EXTRACT(EPOCH FROM (lpep_dropoff_datetime - lpep_pickup_datetime))/60) as avg_trip_duration,
                        AVG(fare_amount) as avg_fare_amount,
                        AVG(tip_amount) as avg_tip_amount,
                        SUM(passenger_count) as total_passengers,
                        AVG(passenger_count) as avg_passengers
                    FROM green_trips
                    WHERE lpep_pickup_datetime IS NOT NULL
                    GROUP BY DATE(lpep_pickup_datetime)
                ),
                fhv_daily AS (
                    SELECT 
                        DATE(pickup_datetime) as trip_date,
                        'fhv' as trip_type,
                        COUNT(*) as total_trips,
                        NULL::numeric as total_revenue,
                        NULL::numeric as avg_trip_distance,
                        AVG(EXTRACT(EPOCH FROM (dropoff_datetime - pickup_datetime))/60) as avg_trip_duration,
                        NULL::numeric as avg_fare_amount,
                        NULL::numeric as avg_tip_amount,
                        NULL::numeric as total_passengers,
                        NULL::numeric as avg_passengers
                    FROM fhv_trips
                    WHERE pickup_datetime IS NOT NULL
                    GROUP BY DATE(pickup_datetime)
                ),
                fhvhv_daily AS (
                    SELECT 
                        DATE(pickup_datetime) as trip_date,
                        'fhvhv' as trip_type,
                        COUNT(*) as total_trips,
                        SUM(base_passenger_fare + COALESCE(tolls, 0) + COALESCE(bcf, 0) + 
                            COALESCE(sales_tax, 0) + COALESCE(congestion_surcharge, 0) + 
                            COALESCE(airport_fee, 0) + COALESCE(tips, 0)) as total_revenue,
                        AVG(trip_miles) as avg_trip_distance,
                        AVG(EXTRACT(EPOCH FROM (dropoff_datetime - pickup_datetime))/60) as avg_trip_duration,
                        AVG(base_passenger_fare) as avg_fare_amount,
                        AVG(tips) as avg_tip_amount,
                        NULL::numeric as total_passengers,
                        NULL::numeric as avg_passengers
                    FROM fhvhv_trips
                    WHERE pickup_datetime IS NOT NULL
                    GROUP BY DATE(pickup_datetime)
                )
                SELECT * FROM yellow_daily
                UNION ALL SELECT * FROM green_daily
                UNION ALL SELECT * FROM fhv_daily
                UNION ALL SELECT * FROM fhvhv_daily
            """))
            
                # Create indexes on daily aggregates
                conn.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_agg_date_type 
                    ON daily_trip_aggregates (trip_date, trip_type)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_daily_agg_date 
                    ON daily_trip_aggregates (trip_date DESC)
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_daily_agg_type 
                    ON daily_trip_aggregates (trip_type)
                """))
                
                logger.info("✓ Daily aggregates view created")
            else:
                logger.info("✓ Daily aggregates view already exists, skipping creation")
            
            # Commit happens automatically with engine.begin()
            logger.info("✓ Materialized views initialization complete")
        
        logger.info("✓ Schema initialization complete!")
        
    except Exception as e:
        logger.error(f"Schema creation error: {e}")
        # Don't fail startup if schema already exists
        if "already exists" not in str(e):
            logger.warning(f"Non-fatal schema error: {e}")


# Create schema on startup
@app.on_event("startup")
async def startup_event():
    create_schema_on_startup()

# CORS configuration
# Support Azure Container Apps URLs with regex patterns for dynamic hostnames
allow_origin_regex = r"https://nyc-(dev|staging|prod)-frontend\.[a-z0-9]+-[a-z0-9]+\.westus\.azurecontainerapps\.io"

# Get additional allowed origins from environment or use defaults for development
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:4200,http://localhost:3000")
allowed_origins = [origin.strip() for origin in cors_origins_str.split(",")]

logger.info(f"CORS allowed origins: {allowed_origins}")
logger.info(f"CORS origin regex: {allow_origin_regex}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.get("/")
@limiter.limit("200/minute")
async def root(request: Request):
    return {
        "message": "NYC TLC Trip Data API", 
        "environment": os.getenv("ENVIRONMENT", "local"),
        "version": "1.0.0"
    }

@app.get("/health")
@limiter.limit("200/minute")
async def health(request: Request, db: Session = Depends(get_db)):
    try:
        # Test database connection with simple query
        db.execute(text("SELECT 1"))
        
        # Quick table existence check (instead of slow COUNT(*))
        tables_exist = {}
        for table in ['yellow_trips', 'green_trips', 'fhv_trips', 'fhvhv_trips']:
            try:
                # Fast existence check without counting rows
                db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                tables_exist[table] = "exists"
            except:
                tables_exist[table] = "missing"
        
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        tables_exist = {}
    
    return {
        "status": "healthy",
        "database": db_status,
        "environment": os.getenv("ENVIRONMENT", "local"),
        "tables": tables_exist
    }

@app.get("/api/items")
async def get_items():
    return {"items": []}


# ==================== Daily Aggregates Endpoints ====================

@app.get("/api/aggregates/daily", response_model=DailyAggregateListResponse)
@limiter.limit("100/minute")
async def get_daily_aggregates(
    request: Request,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    trip_type: Optional[str] = Query(None, description="Filter by trip type: yellow, green, fhv, fhvhv"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    db: Session = Depends(get_db)
):
    """
    Get daily trip aggregates with optional filtering
    Returns: total trips, revenue, avg distance, avg duration per day
    """
    query = text("""
        SELECT 
            trip_date, trip_type, total_trips, total_revenue,
            avg_trip_distance, avg_trip_duration, avg_fare_amount,
            avg_tip_amount, total_passengers, avg_passengers
        FROM daily_trip_aggregates
        WHERE 1=1
        """ + (f" AND trip_date >= :start_date" if start_date else "") +
        (f" AND trip_date <= :end_date" if end_date else "") +
        (f" AND trip_type = :trip_type" if trip_type else "") +
        """
        ORDER BY trip_date DESC, trip_type
        LIMIT :limit
    """)
    
    params = {"limit": limit}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if trip_type:
        params["trip_type"] = trip_type
    
    result = db.execute(query, params)
    rows = result.fetchall()
    
    aggregates = [
        DailyAggregateResponse(
            trip_date=row[0],
            trip_type=row[1],
            total_trips=row[2],
            total_revenue=row[3],
            avg_trip_distance=row[4],
            avg_trip_duration=float(row[5]) if row[5] else None,
            avg_fare_amount=row[6],
            avg_tip_amount=row[7],
            total_passengers=row[8],
            avg_passengers=row[9]
        )
        for row in rows
    ]
    
    return DailyAggregateListResponse(total=len(aggregates), data=aggregates)


@app.get("/api/aggregates/summary")
@limiter.limit("100/minute")
async def get_aggregates_summary(
    request: Request,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics across all trip types for a date range
    """
    query = text("""
        SELECT 
            trip_type,
            COUNT(*) as days,
            SUM(total_trips) as total_trips,
            SUM(total_revenue) as total_revenue,
            AVG(avg_trip_distance) as avg_distance,
            AVG(avg_trip_duration) as avg_duration
        FROM daily_trip_aggregates
        WHERE 1=1
        """ + (f" AND trip_date >= :start_date" if start_date else "") +
        (f" AND trip_date <= :end_date" if end_date else "") +
        """
        GROUP BY trip_type
        ORDER BY trip_type
    """)
    
    params = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    
    result = db.execute(query, params)
    rows = result.fetchall()
    
    summary = [
        {
            "trip_type": row[0],
            "days": row[1],
            "total_trips": row[2],
            "total_revenue": float(row[3]) if row[3] else None,
            "avg_distance": float(row[4]) if row[4] else None,
            "avg_duration": float(row[5]) if row[5] else None
        }
        for row in rows
    ]
    
    return {"summary": summary}


# ==================== Trip Data Endpoints ====================

@app.get("/api/trips", response_model=PaginatedResponse)
@limiter.limit("100/minute")
async def get_trips(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    trip_type: Optional[str] = Query(None, description="Filter by trip type"),
    start_date: Optional[date] = Query(None, description="Filter trips from this date"),
    end_date: Optional[date] = Query(None, description="Filter trips until this date"),
    db: Session = Depends(get_db)
):
    """
    Get paginated trip data from the unified trip_summary_view
    Includes enriched zone information
    """
    offset = (page - 1) * page_size
    
    # Build where clause
    where_conditions = []
    params = {"limit": page_size, "offset": offset}
    
    if trip_type:
        where_conditions.append("trip_type = :trip_type")
        params["trip_type"] = trip_type
    if start_date:
        where_conditions.append("pickup_datetime >= :start_date")
        params["start_date"] = datetime.combine(start_date, datetime.min.time())
    if end_date:
        where_conditions.append("pickup_datetime <= :end_date")
        params["end_date"] = datetime.combine(end_date, datetime.max.time())
    
    where_clause = " AND " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Get total count
    count_query = text(f"""
        SELECT COUNT(*) 
        FROM trip_summary_view 
        WHERE 1=1 {where_clause}
    """)
    total = db.execute(count_query, params).scalar()
    
    # Get paginated data
    data_query = text(f"""
        SELECT 
            id, trip_type, pickup_datetime, dropoff_datetime,
            pu_location_id, pickup_borough, pickup_zone,
            do_location_id, dropoff_borough, dropoff_zone,
            trip_distance, fare_amount, tip_amount, total_amount,
            duration_minutes
        FROM trip_summary_view
        WHERE 1=1 {where_clause}
        ORDER BY pickup_datetime DESC
        LIMIT :limit OFFSET :offset
    """)
    
    result = db.execute(data_query, params)
    rows = result.fetchall()
    
    trips = [
        TripResponse(
            id=row[0],
            trip_type=row[1],
            pickup_datetime=row[2],
            dropoff_datetime=row[3],
            pu_location_id=row[4],
            pickup_borough=row[5],
            pickup_zone=row[6],
            do_location_id=row[7],
            dropoff_borough=row[8],
            dropoff_zone=row[9],
            trip_distance=row[10],
            fare_amount=row[11],
            tip_amount=row[12],
            total_amount=row[13],
            duration_minutes=float(row[14]) if row[14] else None
        )
        for row in rows
    ]
    
    total_pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        data=trips
    )


# ==================== Zone Lookup Endpoint ====================

@app.get("/api/zones")
@limiter.limit("100/minute")
async def get_zones(request: Request, db: Session = Depends(get_db)):
    """Get all taxi zone lookup data"""
    query = text("""
        SELECT location_id, borough, zone, service_zone
        FROM taxi_zone_lookup
        ORDER BY borough, zone
    """)
    
    result = db.execute(query)
    rows = result.fetchall()
    
    zones = [
        {
            "location_id": row[0],
            "borough": row[1],
            "zone": row[2],
            "service_zone": row[3]
        }
        for row in rows
    ]
    
    return {"total": len(zones), "zones": zones}

