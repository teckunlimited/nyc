#!/usr/bin/env python3
"""
Refresh materialized views after loading data
"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://nycadmin:Wg8zL7tt4lN05szaXGTD@nyc-dev-dbfaff08.postgres.database.azure.com:5432/nycdb?sslmode=require"
)

engine = create_engine(DATABASE_URL)

print("Refreshing materialized views...")

with engine.connect() as conn:
    # Refresh trip summary view
    print("  Refreshing trip_summary_view...")
    conn.execute(text("REFRESH MATERIALIZED VIEW trip_summary_view"))
    print("  ✓ trip_summary_view refreshed")
    
    # Refresh daily aggregates
    print("  Refreshing daily_trip_aggregates...")
    conn.execute(text("REFRESH MATERIALIZED VIEW daily_trip_aggregates"))
    print("  ✓ daily_trip_aggregates refreshed")
    
    conn.commit()

print("\n✓ All views refreshed successfully!")

# Show some stats
print("\nData summary:")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT trip_type, COUNT(*) as count, MIN(trip_date) as first_date, MAX(trip_date) as last_date
        FROM daily_trip_aggregates
        GROUP BY trip_type
        ORDER BY trip_type
    """))
    
    for row in result:
        print(f"  {row[0]:10s}: {row[1]:6,} days  ({row[2]} to {row[3]})")
