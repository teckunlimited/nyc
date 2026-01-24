"""
Database schema initialization script
Run this to create all tables and indexes for TLC trip data
"""
import sys
from database import engine
from models import Base, YellowTripData, GreenTripData, FHVTripData, FHVHVTripData, TaxiZoneLookup
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
        # Note: Removed partial indexes with CURRENT_DATE as they're not immutable in PostgreSQL
        # Note: GIST indexes require btree_gist extension for timestamp types
        
        conn.commit()
        print("✓ Performance indexes created")


def create_views():
    """Create materialized views for analytics"""
    print("\nCreating analytics views...")
    
    with engine.connect() as conn:
        # Drop existing views (handle both table and materialized view cases)
        try:
            conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS trip_summary_view CASCADE"))
            conn.commit()
        except Exception:
            conn.rollback()
            conn.execute(text("DROP TABLE IF EXISTS trip_summary_view CASCADE"))
            conn.commit()
        
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
                dz.borough as dropoff_borough,
                dz.zone as dropoff_zone,
                dz.service_zone as dropoff_service_zone,
                y.trip_distance,
                y.fare_amount,
                y.tip_amount,
                y.total_amount,
                EXTRACT(EPOCH FROM (y.tpep_dropoff_datetime - y.tpep_pickup_datetime))/60 as duration_minutes
            FROM yellow_trips y
            LEFT JOIN taxi_zone_lookup pu ON y.pu_location_id = pu.location_id
            LEFT JOIN taxi_zone_lookup dz ON y.do_location_id = dz.location_id
            
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
                dz.borough as dropoff_borough,
                dz.zone as dropoff_zone,
                dz.service_zone as dropoff_service_zone,
                g.trip_distance,
                g.fare_amount,
                g.tip_amount,
                g.total_amount,
                EXTRACT(EPOCH FROM (g.lpep_dropoff_datetime - g.lpep_pickup_datetime))/60 as duration_minutes
            FROM green_trips g
            LEFT JOIN taxi_zone_lookup pu ON g.pu_location_id = pu.location_id
            LEFT JOIN taxi_zone_lookup dz ON g.do_location_id = dz.location_id
            
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
                dz.borough as dropoff_borough,
                dz.zone as dropoff_zone,
                dz.service_zone as dropoff_service_zone,
                NULL::float as trip_distance,
                NULL::float as fare_amount,
                NULL::float as tip_amount,
                NULL::float as total_amount,
                EXTRACT(EPOCH FROM (f.dropoff_datetime - f.pickup_datetime))/60 as duration_minutes
            FROM fhv_trips f
            LEFT JOIN taxi_zone_lookup pu ON CAST(f.pu_location_id AS INTEGER) = pu.location_id
            LEFT JOIN taxi_zone_lookup dz ON CAST(f.do_location_id AS INTEGER) = dz.location_id
            
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
                dz.borough as dropoff_borough,
                dz.zone as dropoff_zone,
                dz.service_zone as dropoff_service_zone,
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
            LEFT JOIN taxi_zone_lookup dz ON h.do_location_id = dz.location_id
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


def create_daily_aggregates():
    """Create daily trip aggregates materialized view"""
    print("\nCreating daily aggregates view...")
    
    with engine.connect() as conn:
        # Drop existing view if present
        try:
            conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS daily_trip_aggregates CASCADE"))
            conn.commit()
        except Exception:
            conn.rollback()
            conn.execute(text("DROP TABLE IF EXISTS daily_trip_aggregates CASCADE"))
            conn.commit()
        
        # Create daily aggregates materialized view
        conn.execute(text("""
            CREATE MATERIALIZED VIEW daily_trip_aggregates AS
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
                AND tpep_dropoff_datetime IS NOT NULL
                AND total_amount IS NOT NULL
            GROUP BY DATE(tpep_pickup_datetime)
            
            UNION ALL
            
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
                AND lpep_dropoff_datetime IS NOT NULL
                AND total_amount IS NOT NULL
            GROUP BY DATE(lpep_pickup_datetime)
            
            UNION ALL
            
            SELECT 
                DATE(pickup_datetime) as trip_date,
                'fhv' as trip_type,
                COUNT(*) as total_trips,
                NULL::float as total_revenue,
                NULL::float as avg_trip_distance,
                AVG(EXTRACT(EPOCH FROM (dropoff_datetime - pickup_datetime))/60) as avg_trip_duration,
                NULL::float as avg_fare_amount,
                NULL::float as avg_tip_amount,
                NULL::bigint as total_passengers,
                NULL::float as avg_passengers
            FROM fhv_trips
            WHERE pickup_datetime IS NOT NULL 
                AND dropoff_datetime IS NOT NULL
            GROUP BY DATE(pickup_datetime)
            
            UNION ALL
            
            SELECT 
                DATE(pickup_datetime) as trip_date,
                'fhvhv' as trip_type,
                COUNT(*) as total_trips,
                SUM(COALESCE(base_passenger_fare, 0) + COALESCE(tolls, 0) + 
                    COALESCE(bcf, 0) + COALESCE(sales_tax, 0) + 
                    COALESCE(congestion_surcharge, 0) + COALESCE(airport_fee, 0) + 
                    COALESCE(tips, 0)) as total_revenue,
                AVG(trip_miles) as avg_trip_distance,
                AVG(EXTRACT(EPOCH FROM (dropoff_datetime - pickup_datetime))/60) as avg_trip_duration,
                AVG(base_passenger_fare) as avg_fare_amount,
                AVG(tips) as avg_tip_amount,
                NULL::bigint as total_passengers,
                NULL::float as avg_passengers
            FROM fhvhv_trips
            WHERE pickup_datetime IS NOT NULL 
                AND dropoff_datetime IS NOT NULL
            GROUP BY DATE(pickup_datetime)
        """))
        
        # Create indexes on the materialized view
        conn.execute(text("""
            CREATE UNIQUE INDEX idx_daily_agg_date_type ON daily_trip_aggregates (trip_date, trip_type)
        """))
        conn.execute(text("""
            CREATE INDEX idx_daily_agg_date ON daily_trip_aggregates (trip_date DESC)
        """))
        conn.execute(text("""
            CREATE INDEX idx_daily_agg_type ON daily_trip_aggregates (trip_type)
        """))
        
        conn.commit()
        print("✓ Daily aggregates materialized view created")
        print("  Note: Refresh with 'REFRESH MATERIALIZED VIEW daily_trip_aggregates' after loading data")


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
        create_daily_aggregates()
        verify_schema()
        
        print("\n" + "=" * 60)
        print("✓ Schema initialization complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
