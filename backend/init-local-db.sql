-- NYC TLC Database Schema Initialization
-- This runs automatically when PostgreSQL container starts

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Create tables
CREATE TABLE IF NOT EXISTS yellow_trips (
    id SERIAL PRIMARY KEY,
    vendorid INTEGER,
    tpep_pickup_datetime TIMESTAMP,
    tpep_dropoff_datetime TIMESTAMP,
    passenger_count DOUBLE PRECISION,
    trip_distance DOUBLE PRECISION,
    ratecodeid DOUBLE PRECISION,
    store_and_fwd_flag TEXT,
    pulocationid INTEGER,
    dolocationid INTEGER,
    payment_type DOUBLE PRECISION,
    fare_amount DOUBLE PRECISION,
    extra DOUBLE PRECISION,
    mta_tax DOUBLE PRECISION,
    tip_amount DOUBLE PRECISION,
    tolls_amount DOUBLE PRECISION,
    improvement_surcharge DOUBLE PRECISION,
    total_amount DOUBLE PRECISION,
    congestion_surcharge DOUBLE PRECISION,
    airport_fee DOUBLE PRECISION,
    cbd_congestion_fee DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS green_trips (
    id SERIAL PRIMARY KEY,
    vendorid INTEGER,
    lpep_pickup_datetime TIMESTAMP,
    lpep_dropoff_datetime TIMESTAMP,
    store_and_fwd_flag TEXT,
    ratecodeid DOUBLE PRECISION,
    pulocationid INTEGER,
    dolocationid INTEGER,
    passenger_count DOUBLE PRECISION,
    trip_distance DOUBLE PRECISION,
    fare_amount DOUBLE PRECISION,
    extra DOUBLE PRECISION,
    mta_tax DOUBLE PRECISION,
    tip_amount DOUBLE PRECISION,
    tolls_amount DOUBLE PRECISION,
    ehail_fee DOUBLE PRECISION,
    improvement_surcharge DOUBLE PRECISION,
    total_amount DOUBLE PRECISION,
    payment_type DOUBLE PRECISION,
    trip_type DOUBLE PRECISION,
    congestion_surcharge DOUBLE PRECISION,
    cbd_congestion_fee DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fhv_trips (
    id SERIAL PRIMARY KEY,
    dispatching_base_num TEXT,
    pickup_datetime TIMESTAMP,
    dropoff_datetime TIMESTAMP,
    pulocationid INTEGER,
    dolocationid INTEGER,
    sr_flag INTEGER,
    affiliated_base_number TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fhvhv_trips (
    id SERIAL PRIMARY KEY,
    hvfhs_license_num TEXT,
    dispatching_base_num TEXT,
    originating_base_num TEXT,
    request_datetime TIMESTAMP,
    on_scene_datetime TIMESTAMP,
    pickup_datetime TIMESTAMP,
    dropoff_datetime TIMESTAMP,
    pulocationid INTEGER,
    dolocationid INTEGER,
    trip_miles DOUBLE PRECISION,
    trip_time DOUBLE PRECISION,
    base_passenger_fare DOUBLE PRECISION,
    tolls DOUBLE PRECISION,
    bcf DOUBLE PRECISION,
    sales_tax DOUBLE PRECISION,
    congestion_surcharge DOUBLE PRECISION,
    airport_fee DOUBLE PRECISION,
    tips DOUBLE PRECISION,
    driver_pay DOUBLE PRECISION,
    shared_request_flag TEXT,
    shared_match_flag TEXT,
    access_a_ride_flag TEXT,
    wav_request_flag TEXT,
    wav_match_flag TEXT,
    cbd_congestion_fee DOUBLE PRECISION,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS taxi_zone_lookup (
    location_id INTEGER PRIMARY KEY,
    borough TEXT,
    zone TEXT,
    service_zone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create file tracking table for duplicate prevention
CREATE TABLE IF NOT EXISTS loaded_files (
    id SERIAL PRIMARY KEY,
    filename TEXT UNIQUE NOT NULL,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_count INTEGER,
    trip_type TEXT
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_yellow_pickup ON yellow_trips(tpep_pickup_datetime);
CREATE INDEX IF NOT EXISTS idx_yellow_dropoff ON yellow_trips(tpep_dropoff_datetime);
CREATE INDEX IF NOT EXISTS idx_yellow_pu_location ON yellow_trips(pulocationid);
CREATE INDEX IF NOT EXISTS idx_yellow_do_location ON yellow_trips(dolocationid);

CREATE INDEX IF NOT EXISTS idx_green_pickup ON green_trips(lpep_pickup_datetime);
CREATE INDEX IF NOT EXISTS idx_green_dropoff ON green_trips(lpep_dropoff_datetime);
CREATE INDEX IF NOT EXISTS idx_green_pu_location ON green_trips(pulocationid);
CREATE INDEX IF NOT EXISTS idx_green_do_location ON green_trips(dolocationid);

CREATE INDEX IF NOT EXISTS idx_fhv_pickup ON fhv_trips(pickup_datetime);
CREATE INDEX IF NOT EXISTS idx_fhv_dropoff ON fhv_trips(dropoff_datetime);
CREATE INDEX IF NOT EXISTS idx_fhv_pu_location ON fhv_trips(pulocationid);
CREATE INDEX IF NOT EXISTS idx_fhv_do_location ON fhv_trips(dolocationid);

CREATE INDEX IF NOT EXISTS idx_fhvhv_pickup ON fhvhv_trips(pickup_datetime);
CREATE INDEX IF NOT EXISTS idx_fhvhv_dropoff ON fhvhv_trips(dropoff_datetime);
CREATE INDEX IF NOT EXISTS idx_fhvhv_pu_location ON fhvhv_trips(pulocationid);
CREATE INDEX IF NOT EXISTS idx_fhvhv_do_location ON fhvhv_trips(dolocationid);

-- Create trigger function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for all tables
CREATE TRIGGER update_yellow_trips_updated_at BEFORE UPDATE ON yellow_trips
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_green_trips_updated_at BEFORE UPDATE ON green_trips
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhv_trips_updated_at BEFORE UPDATE ON fhv_trips
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fhvhv_trips_updated_at BEFORE UPDATE ON fhvhv_trips
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create materialized views for performance
-- These will be empty initially and populated after data is loaded
-- Using WITH NO DATA to create the structure without data

CREATE MATERIALIZED VIEW IF NOT EXISTS trip_summary_view AS
SELECT 
    y.id,
    'yellow'::text as trip_type,
    y.tpep_pickup_datetime as pickup_datetime,
    y.tpep_dropoff_datetime as dropoff_datetime,
    y.pulocationid as pu_location_id,
    pu_zone.borough as pickup_borough,
    pu_zone.zone as pickup_zone,
    pu_zone.service_zone as pickup_service_zone,
    y.dolocationid as do_location_id,
    do_zone.borough as dropoff_borough,
    do_zone.zone as dropoff_zone,
    do_zone.service_zone as dropoff_service_zone,
    y.trip_distance,
    y.fare_amount,
    y.tip_amount,
    y.total_amount,
    EXTRACT(EPOCH FROM (y.tpep_dropoff_datetime - y.tpep_pickup_datetime))/60 as duration_minutes
FROM yellow_trips y
LEFT JOIN taxi_zone_lookup AS pu_zone ON y.pulocationid = pu_zone.location_id
LEFT JOIN taxi_zone_lookup AS do_zone ON y.dolocationid = do_zone.location_id
WHERE y.tpep_pickup_datetime IS NOT NULL AND y.tpep_dropoff_datetime IS NOT NULL

UNION ALL

SELECT 
    g.id,
    'green'::text as trip_type,
    g.lpep_pickup_datetime as pickup_datetime,
    g.lpep_dropoff_datetime as dropoff_datetime,
    g.pulocationid as pu_location_id,
    pu_zone.borough as pickup_borough,
    pu_zone.zone as pickup_zone,
    pu_zone.service_zone as pickup_service_zone,
    g.dolocationid as do_location_id,
    do_zone.borough as dropoff_borough,
    do_zone.zone as dropoff_zone,
    do_zone.service_zone as dropoff_service_zone,
    g.trip_distance,
    g.fare_amount,
    g.tip_amount,
    g.total_amount,
    EXTRACT(EPOCH FROM (g.lpep_dropoff_datetime - g.lpep_pickup_datetime))/60 as duration_minutes
FROM green_trips g
LEFT JOIN taxi_zone_lookup AS pu_zone ON g.pulocationid = pu_zone.location_id
LEFT JOIN taxi_zone_lookup AS do_zone ON g.dolocationid = do_zone.location_id
WHERE g.lpep_pickup_datetime IS NOT NULL AND g.lpep_dropoff_datetime IS NOT NULL

UNION ALL

SELECT 
    f.id,
    'fhv'::text as trip_type,
    f.pickup_datetime,
    f.dropoff_datetime,
    f.pulocationid as pu_location_id,
    pu_zone.borough as pickup_borough,
    pu_zone.zone as pickup_zone,
    pu_zone.service_zone as pickup_service_zone,
    f.dolocationid as do_location_id,
    do_zone.borough as dropoff_borough,
    do_zone.zone as dropoff_zone,
    do_zone.service_zone as dropoff_service_zone,
    NULL::double precision as trip_distance,
    NULL::double precision as fare_amount,
    NULL::double precision as tip_amount,
    NULL::double precision as total_amount,
    EXTRACT(EPOCH FROM (f.dropoff_datetime - f.pickup_datetime))/60 as duration_minutes
FROM fhv_trips f
LEFT JOIN taxi_zone_lookup AS pu_zone ON f.pulocationid = pu_zone.location_id
LEFT JOIN taxi_zone_lookup AS do_zone ON f.dolocationid = do_zone.location_id
WHERE f.pickup_datetime IS NOT NULL AND f.dropoff_datetime IS NOT NULL

UNION ALL

SELECT 
    h.id,
    'fhvhv'::text as trip_type,
    h.pickup_datetime,
    h.dropoff_datetime,
    h.pulocationid as pu_location_id,
    pu_zone.borough as pickup_borough,
    pu_zone.zone as pickup_zone,
    pu_zone.service_zone as pickup_service_zone,
    h.dolocationid as do_location_id,
    do_zone.borough as dropoff_borough,
    do_zone.zone as dropoff_zone,
    do_zone.service_zone as dropoff_service_zone,
    h.trip_miles as trip_distance,
    h.base_passenger_fare as fare_amount,
    h.tips as tip_amount,
    (COALESCE(h.base_passenger_fare, 0) + COALESCE(h.tolls, 0) + 
     COALESCE(h.bcf, 0) + COALESCE(h.sales_tax, 0) + 
     COALESCE(h.congestion_surcharge, 0) + COALESCE(h.airport_fee, 0) + 
     COALESCE(h.tips, 0)) as total_amount,
    EXTRACT(EPOCH FROM (h.dropoff_datetime - h.pickup_datetime))/60 as duration_minutes
FROM fhvhv_trips h
LEFT JOIN taxi_zone_lookup AS pu_zone ON h.pulocationid = pu_zone.location_id
LEFT JOIN taxi_zone_lookup AS do_zone ON h.dolocationid = do_zone.location_id
WHERE h.pickup_datetime IS NOT NULL AND h.dropoff_datetime IS NOT NULL
WITH NO DATA;

-- Create indexes on trip_summary_view
CREATE INDEX IF NOT EXISTS idx_summary_trip_type ON trip_summary_view (trip_type);
CREATE INDEX IF NOT EXISTS idx_summary_pickup_date ON trip_summary_view (pickup_datetime);
CREATE INDEX IF NOT EXISTS idx_summary_locations ON trip_summary_view (pu_location_id, do_location_id);

-- Create daily_trip_aggregates materialized view
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_trip_aggregates AS
WITH yellow_daily AS (
    SELECT 
        DATE(tpep_pickup_datetime) as trip_date,
        'yellow'::text as trip_type,
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
        'green'::text as trip_type,
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
        'fhv'::text as trip_type,
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
        'fhvhv'::text as trip_type,
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
WITH NO DATA;

-- Create indexes on daily_trip_aggregates
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_agg_date_type 
    ON daily_trip_aggregates (trip_date, trip_type);
CREATE INDEX IF NOT EXISTS idx_daily_agg_date 
    ON daily_trip_aggregates (trip_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_agg_type 
    ON daily_trip_aggregates (trip_type);
