"""
Database schema initialization script
Run this to create all tables and indexes for TLC trip data
"""
import sys
from database import engine
from models import Base, YellowTripData, GreenTripData, FHVTripData, FHVHVTripData
from sqlalchemy import text


def create_tables():
    """Create all tables defined in models"""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Tables created successfully")


def create_partitions():
    """
    Create table partitions by month for better query performance
    This is optional but recommended for large datasets
    """
    print("\nSetting up table partitioning...")
    
    # Note: Native PostgreSQL partitioning requires PostgreSQL 10+
    # For now, we'll use indexes. Future enhancement could add declarative partitioning.
    
    with engine.connect() as conn:
        # Create additional performance indexes
        
        # Partial indexes for common filters
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
        
        # GiST indexes for range queries on datetime
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_yellow_datetime_range 
            ON yellow_trips USING GIST (tpep_pickup_datetime, tpep_dropoff_datetime)
        """))
        
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_green_datetime_range 
            ON green_trips USING GIST (lpep_pickup_datetime, lpep_dropoff_datetime)
        """))
        
        conn.commit()
        print("✓ Performance indexes created")


def create_views():
    """Create materialized views for analytics"""
    print("\nCreating analytics views...")
    
    with engine.connect() as conn:
        # Drop existing views
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
        """))
        
        # Create indexes on materialized view
        conn.execute(text("""
            CREATE INDEX idx_summary_trip_type ON trip_summary_view (trip_type)
        """))
        conn.execute(text("""
            CREATE INDEX idx_summary_pickup_date ON trip_summary_view (pickup_datetime)
        """))
        conn.execute(text("""
            CREATE INDEX idx_summary_locations ON trip_summary_view (pu_location_id, do_location_id)
        """))
        
        conn.commit()
        print("✓ Materialized view created")
        print("  Note: Refresh with 'REFRESH MATERIALIZED VIEW trip_summary_view' after loading data")


def verify_schema():
    """Verify that all tables were created successfully"""
    print("\nVerifying schema...")
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        
        tables = [row[0] for row in result]
        expected_tables = ['yellow_trips', 'green_trips', 'fhv_trips', 'fhvhv_trips']
        
        print(f"Found {len(tables)} tables:")
        for table in tables:
            status = "✓" if table in expected_tables else "?"
            print(f"  {status} {table}")
        
        # Check indexes
        result = conn.execute(text("""
            SELECT 
                schemaname, 
                tablename, 
                COUNT(*) as index_count
            FROM pg_indexes
            WHERE schemaname = 'public'
            GROUP BY schemaname, tablename
            ORDER BY tablename
        """))
        
        print("\nIndexes per table:")
        for row in result:
            print(f"  {row[1]}: {row[2]} indexes")


if __name__ == "__main__":
    print("=" * 60)
    print("TLC Trip Data - Database Schema Initialization")
    print("=" * 60)
    
    try:
        create_tables()
        create_partitions()
        create_views()
        verify_schema()
        
        print("\n" + "=" * 60)
        print("✓ Schema initialization complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
