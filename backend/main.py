from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
import logging
from database import get_db, engine, Base
from models import YellowTripData, GreenTripData, FHVTripData, FHVHVTripData, TaxiZoneLookup

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="NYC TLC Trip Data API", version="1.0.0")


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
            # Create partial indexes for recent trips (performance optimization)
            logger.info("Creating performance indexes...")
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_yellow_recent_trips 
                ON yellow_trips (tpep_pickup_datetime DESC) 
                WHERE tpep_pickup_datetime > CURRENT_DATE - INTERVAL '90 days'
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_green_recent_trips 
                ON green_trips (lpep_pickup_datetime DESC) 
                WHERE lpep_pickup_datetime > CURRENT_DATE - INTERVAL '90 days'
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_fhv_recent_trips 
                ON fhv_trips (pickup_datetime DESC) 
                WHERE pickup_datetime > CURRENT_DATE - INTERVAL '90 days'
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_fhvhv_recent_trips 
                ON fhvhv_trips (pickup_datetime DESC) 
                WHERE pickup_datetime > CURRENT_DATE - INTERVAL '90 days'
            """))
            
            # Create GiST indexes for datetime range queries
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_yellow_datetime_range 
                ON yellow_trips USING GIST (tpep_pickup_datetime, tpep_dropoff_datetime)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_green_datetime_range 
                ON green_trips USING GIST (lpep_pickup_datetime, lpep_dropoff_datetime)
            """))
            
            logger.info("✓ Performance indexes created")
            
            # Create materialized view for cross-trip analytics
            logger.info("Creating materialized view...")
            
            # Drop existing view if it exists
            conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS trip_summary_view"))
            
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
            
            # Commit happens automatically with engine.begin()
            logger.info("✓ Materialized view created")
        
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "NYC TLC Trip Data API", 
        "environment": os.getenv("ENVIRONMENT", "local"),
        "version": "1.0.0"
    }

@app.get("/health")
async def health(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        
        # Get table counts
        stats = {}
        for table in ['yellow_trips', 'green_trips', 'fhv_trips', 'fhvhv_trips']:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                stats[table] = result.scalar()
            except:
                stats[table] = 0
        
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        stats = {}
    
    return {
        "status": "healthy",
        "database": db_status,
        "environment": os.getenv("ENVIRONMENT", "local"),
        "trip_counts": stats
    }

@app.get("/api/items")
async def get_items():
    return {"items": []}
