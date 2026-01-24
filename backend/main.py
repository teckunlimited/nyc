from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
import logging
from database import get_db, engine, Base
from models import YellowTripData, GreenTripData, FHVTripData, FHVHVTripData

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
        
        # Create all tables from models
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Tables created")
        
        # Force commit by using begin() context
        with engine.begin() as conn:
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
            
            # Create unified trip summary view
            conn.execute(text("""
                CREATE MATERIALIZED VIEW trip_summary_view AS
                SELECT 
                    id,
                    'yellow' as trip_type,
                    tpep_pickup_datetime as pickup_datetime,
                    tpep_dropoff_datetime as dropoff_datetime,
                    pu_location_id,
                    do_location_id,
                    trip_distance,
                    fare_amount,
                    tip_amount,
                    total_amount,
                    EXTRACT(EPOCH FROM (tpep_dropoff_datetime - tpep_pickup_datetime))/60 as duration_minutes
                FROM yellow_trips
                WHERE tpep_pickup_datetime IS NOT NULL AND tpep_dropoff_datetime IS NOT NULL
                
                UNION ALL
                
                SELECT 
                    id,
                    'green' as trip_type,
                    lpep_pickup_datetime as pickup_datetime,
                    lpep_dropoff_datetime as dropoff_datetime,
                    pu_location_id,
                    do_location_id,
                    trip_distance,
                    fare_amount,
                    tip_amount,
                    total_amount,
                    EXTRACT(EPOCH FROM (lpep_dropoff_datetime - lpep_pickup_datetime))/60 as duration_minutes
                FROM green_trips
                WHERE lpep_pickup_datetime IS NOT NULL AND lpep_dropoff_datetime IS NOT NULL
                
                UNION ALL
                
                SELECT 
                    id,
                    'fhv' as trip_type,
                    pickup_datetime,
                    dropoff_datetime,
                    CAST(pu_location_id AS INTEGER) as pu_location_id,
                    CAST(do_location_id AS INTEGER) as do_location_id,
                    NULL::float as trip_distance,
                    NULL::float as fare_amount,
                    NULL::float as tip_amount,
                    NULL::float as total_amount,
                    EXTRACT(EPOCH FROM (dropoff_datetime - pickup_datetime))/60 as duration_minutes
                FROM fhv_trips
                WHERE pickup_datetime IS NOT NULL AND dropoff_datetime IS NOT NULL
                
                UNION ALL
                
                SELECT 
                    id,
                    'fhvhv' as trip_type,
                    pickup_datetime,
                    dropoff_datetime,
                    pu_location_id,
                    do_location_id,
                    trip_miles as trip_distance,
                    base_passenger_fare as fare_amount,
                    tips as tip_amount,
                    (COALESCE(base_passenger_fare, 0) + COALESCE(tolls, 0) + 
                     COALESCE(bcf, 0) + COALESCE(sales_tax, 0) + 
                     COALESCE(congestion_surcharge, 0) + COALESCE(airport_fee, 0) + 
                     COALESCE(tips, 0)) as total_amount,
                    EXTRACT(EPOCH FROM (dropoff_datetime - pickup_datetime))/60 as duration_minutes
                FROM fhvhv_trips
                WHERE pickup_datetime IS NOT NULL AND dropoff_datetime IS NOT NULL
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
