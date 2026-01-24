"""
TLC Trip Data Models for PostgreSQL
Supports Yellow, Green, FHV, and FHVHV trip data with optimized indexing for analytics
"""
from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime

Base = declarative_base()


class YellowTripData(Base):
    """Yellow Taxi Trip Records"""
    __tablename__ = 'yellow_trips'
    
    # Primary key (auto-generated)
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Source columns
    vendor_id = Column(Integer)
    tpep_pickup_datetime = Column(DateTime, nullable=False, index=True)
    tpep_dropoff_datetime = Column(DateTime, nullable=False, index=True)
    passenger_count = Column(Float)
    trip_distance = Column(Float, index=True)
    rate_code_id = Column(Float)
    store_and_fwd_flag = Column(String(1))
    pu_location_id = Column(Integer, index=True)
    do_location_id = Column(Integer, index=True)
    payment_type = Column(Integer, index=True)
    fare_amount = Column(Float, index=True)
    extra = Column(Float)
    mta_tax = Column(Float)
    tip_amount = Column(Float)
    tolls_amount = Column(Float)
    improvement_surcharge = Column(Float)
    total_amount = Column(Float, index=True)
    congestion_surcharge = Column(Float)
    airport_fee = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @hybrid_property
    def trip_duration_minutes(self):
        """Calculated trip duration in minutes"""
        if self.tpep_pickup_datetime and self.tpep_dropoff_datetime:
            delta = self.tpep_dropoff_datetime - self.tpep_pickup_datetime
            return delta.total_seconds() / 60
        return None
    
    @hybrid_property
    def trip_date(self):
        """Extract date from pickup datetime for partitioning/filtering"""
        if self.tpep_pickup_datetime:
            return self.tpep_pickup_datetime.date()
        return None
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_yellow_pickup_date', 'tpep_pickup_datetime'),
        Index('idx_yellow_location_pair', 'pu_location_id', 'do_location_id'),
        Index('idx_yellow_datetime_location', 'tpep_pickup_datetime', 'pu_location_id'),
        Index('idx_yellow_fare_analysis', 'fare_amount', 'tip_amount', 'total_amount'),
        Index('idx_yellow_time_distance', 'tpep_pickup_datetime', 'trip_distance'),
    )


class GreenTripData(Base):
    """Green Taxi Trip Records"""
    __tablename__ = 'green_trips'
    
    # Primary key (auto-generated)
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Source columns
    vendor_id = Column(Integer)
    lpep_pickup_datetime = Column(DateTime, nullable=False, index=True)
    lpep_dropoff_datetime = Column(DateTime, nullable=False, index=True)
    store_and_fwd_flag = Column(String(1))
    rate_code_id = Column(Float)
    pu_location_id = Column(Integer, index=True)
    do_location_id = Column(Integer, index=True)
    passenger_count = Column(Float)
    trip_distance = Column(Float, index=True)
    fare_amount = Column(Float, index=True)
    extra = Column(Float)
    mta_tax = Column(Float)
    tip_amount = Column(Float)
    tolls_amount = Column(Float)
    ehail_fee = Column(Integer)
    improvement_surcharge = Column(Float)
    total_amount = Column(Float, index=True)
    payment_type = Column(Float, index=True)
    trip_type = Column(Float)
    congestion_surcharge = Column(Float)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @hybrid_property
    def trip_duration_minutes(self):
        """Calculated trip duration in minutes"""
        if self.lpep_pickup_datetime and self.lpep_dropoff_datetime:
            delta = self.lpep_dropoff_datetime - self.lpep_pickup_datetime
            return delta.total_seconds() / 60
        return None
    
    @hybrid_property
    def trip_date(self):
        """Extract date from pickup datetime for partitioning/filtering"""
        if self.lpep_pickup_datetime:
            return self.lpep_pickup_datetime.date()
        return None
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_green_pickup_date', 'lpep_pickup_datetime'),
        Index('idx_green_location_pair', 'pu_location_id', 'do_location_id'),
        Index('idx_green_datetime_location', 'lpep_pickup_datetime', 'pu_location_id'),
        Index('idx_green_fare_analysis', 'fare_amount', 'tip_amount', 'total_amount'),
        Index('idx_green_time_distance', 'lpep_pickup_datetime', 'trip_distance'),
    )


class FHVTripData(Base):
    """For-Hire Vehicle Trip Records"""
    __tablename__ = 'fhv_trips'
    
    # Primary key (auto-generated)
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Source columns
    dispatching_base_num = Column(String(10), index=True)
    pickup_datetime = Column(DateTime, nullable=False, index=True)
    dropoff_datetime = Column(DateTime, nullable=False, index=True)
    pu_location_id = Column(Float, index=True)
    do_location_id = Column(Float, index=True)
    sr_flag = Column(Integer)  # Shared ride flag
    affiliated_base_number = Column(String(10))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @hybrid_property
    def trip_duration_minutes(self):
        """Calculated trip duration in minutes"""
        if self.pickup_datetime and self.dropoff_datetime:
            delta = self.dropoff_datetime - self.pickup_datetime
            return delta.total_seconds() / 60
        return None
    
    @hybrid_property
    def trip_date(self):
        """Extract date from pickup datetime for partitioning/filtering"""
        if self.pickup_datetime:
            return self.pickup_datetime.date()
        return None
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_fhv_pickup_date', 'pickup_datetime'),
        Index('idx_fhv_location_pair', 'pu_location_id', 'do_location_id'),
        Index('idx_fhv_base_datetime', 'dispatching_base_num', 'pickup_datetime'),
        Index('idx_fhv_shared_rides', 'sr_flag', 'pickup_datetime'),
    )


class FHVHVTripData(Base):
    """High-Volume For-Hire Vehicle Trip Records (Uber, Lyft, etc.)"""
    __tablename__ = 'fhvhv_trips'
    
    # Primary key (auto-generated)
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Source columns
    hvfhs_license_num = Column(String(10), index=True)  # HV-0002 (Uber), HV-0003 (Lyft), etc.
    dispatching_base_num = Column(String(10), index=True)
    originating_base_num = Column(String(10))
    request_datetime = Column(DateTime, index=True)
    on_scene_datetime = Column(DateTime)
    pickup_datetime = Column(DateTime, nullable=False, index=True)
    dropoff_datetime = Column(DateTime, nullable=False, index=True)
    pu_location_id = Column(Integer, index=True)
    do_location_id = Column(Integer, index=True)
    trip_miles = Column(Float, index=True)
    trip_time = Column(Integer)  # in seconds
    base_passenger_fare = Column(Float)
    tolls = Column(Float)
    bcf = Column(Float)  # Black Car Fund
    sales_tax = Column(Float)
    congestion_surcharge = Column(Float)
    airport_fee = Column(Float)
    tips = Column(Float)
    driver_pay = Column(Float, index=True)
    shared_request_flag = Column(String(1))
    shared_match_flag = Column(String(1))
    access_a_ride_flag = Column(String(1))
    wav_request_flag = Column(String(1))  # Wheelchair accessible vehicle
    wav_match_flag = Column(String(1))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @hybrid_property
    def total_fare(self):
        """Calculate total fare from components"""
        components = [
            self.base_passenger_fare or 0,
            self.tolls or 0,
            self.bcf or 0,
            self.sales_tax or 0,
            self.congestion_surcharge or 0,
            self.airport_fee or 0,
            self.tips or 0
        ]
        return sum(components)
    
    @hybrid_property
    def trip_duration_minutes(self):
        """Calculated trip duration in minutes"""
        if self.pickup_datetime and self.dropoff_datetime:
            delta = self.dropoff_datetime - self.pickup_datetime
            return delta.total_seconds() / 60
        return None
    
    @hybrid_property
    def wait_time_minutes(self):
        """Time between request and pickup"""
        if self.request_datetime and self.pickup_datetime:
            delta = self.pickup_datetime - self.request_datetime
            return delta.total_seconds() / 60
        return None
    
    @hybrid_property
    def trip_date(self):
        """Extract date from pickup datetime for partitioning/filtering"""
        if self.pickup_datetime:
            return self.pickup_datetime.date()
        return None
    
    # Composite indexes for common query patterns
    __table_args__ = (
        Index('idx_fhvhv_pickup_date', 'pickup_datetime'),
        Index('idx_fhvhv_location_pair', 'pu_location_id', 'do_location_id'),
        Index('idx_fhvhv_company_datetime', 'hvfhs_license_num', 'pickup_datetime'),
        Index('idx_fhvhv_shared_rides', 'shared_request_flag', 'shared_match_flag', 'pickup_datetime'),
        Index('idx_fhvhv_fare_analysis', 'base_passenger_fare', 'tips', 'driver_pay'),
        Index('idx_fhvhv_time_distance', 'pickup_datetime', 'trip_miles'),
        Index('idx_fhvhv_wav', 'wav_request_flag', 'wav_match_flag'),
    )


# Summary view for cross-trip type analytics
class TripSummary(Base):
    """Materialized view combining all trip types for aggregate analytics"""
    __tablename__ = 'trip_summary_view'
    __table_args__ = {'info': {'is_view': True}}
    
    id = Column(BigInteger, primary_key=True)
    trip_type = Column(String(10))  # 'yellow', 'green', 'fhv', 'fhvhv'
    pickup_datetime = Column(DateTime, index=True)
    dropoff_datetime = Column(DateTime)
    pu_location_id = Column(Integer, index=True)
    do_location_id = Column(Integer, index=True)
    trip_distance = Column(Float)
    fare_amount = Column(Float)
    tip_amount = Column(Float)
    total_amount = Column(Float)
