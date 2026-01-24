"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


class TripBase(BaseModel):
    """Base trip data schema"""
    trip_type: str
    pickup_datetime: datetime
    dropoff_datetime: datetime
    pu_location_id: Optional[int] = None
    do_location_id: Optional[int] = None
    trip_distance: Optional[float] = None
    fare_amount: Optional[float] = None
    tip_amount: Optional[float] = None
    total_amount: Optional[float] = None
    
    class Config:
        from_attributes = True


class TripResponse(TripBase):
    """Trip response with enriched data"""
    id: int
    pickup_borough: Optional[str] = None
    pickup_zone: Optional[str] = None
    dropoff_borough: Optional[str] = None
    dropoff_zone: Optional[str] = None
    duration_minutes: Optional[float] = None


class DailyAggregateResponse(BaseModel):
    """Daily aggregate statistics response"""
    trip_date: date
    trip_type: str
    total_trips: int
    total_revenue: Optional[float] = None
    avg_trip_distance: Optional[float] = None
    avg_trip_duration: Optional[float] = None
    avg_fare_amount: Optional[float] = None
    avg_tip_amount: Optional[float] = None
    total_passengers: Optional[float] = None
    avg_passengers: Optional[float] = None
    
    class Config:
        from_attributes = True


class PaginatedResponse(BaseModel):
    """Paginated response wrapper"""
    total: int
    page: int
    page_size: int
    total_pages: int
    data: List[TripResponse]


class DailyAggregateListResponse(BaseModel):
    """Daily aggregates list response"""
    total: int
    data: List[DailyAggregateResponse]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    environment: str
    trip_counts: dict

