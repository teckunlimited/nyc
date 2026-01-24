# Backend API Unit Tests

## Overview

Comprehensive unit tests for the NYC TLC Trip Data FastAPI backend. Tests cover all API endpoints, query parameters, pagination, filtering, and error handling.

## Test Coverage

### Passing Tests (15/24)

✅ **Health & System Tests**
- `test_health_check` - Health endpoint returns correct status
- `test_root_endpoint` - Root endpoint basic functionality
- `test_items_endpoint` - Items endpoint returns list

✅ **Daily Aggregates Tests**
- `test_get_daily_aggregates_all` - Get all aggregates without filters
- `test_get_daily_aggregates_with_limit` - Limit parameter works correctly
- `test_get_daily_aggregates_validation` - Parameter validation (422 errors)
- `test_get_daily_aggregates_response_structure` - Response schema validation
- `test_get_aggregates_summary` - Summary endpoint returns grouped data
- `test_get_aggregates_summary_with_date_range` - Date filtering in summary

✅ **Trip Data Tests**
- `test_get_trips_default_pagination` - Default pagination (page 1, size 100)
- `test_get_trips_with_date_filter` - Date range filtering works
- `test_get_trips_response_structure` - Response includes all required fields
- `test_get_trips_pagination_validation` - Validates page/page_size params

✅ **Error Handling Tests**
- `test_invalid_endpoint` - 404 for non-existent endpoints
- `test_method_not_allowed` - 405 for wrong HTTP methods

### Known Issues (9 tests)

⚠️ **Test Data Mismatches** (6 tests)
- Filter tests expect exact counts but SQLite test data differs slightly
- Fixable by adjusting expected values in assertions

⚠️ **Missing Table** (3 tests)
- `taxi_zone_lookup` table not created in SQLite test database
- Requires adding table creation to test_db fixture

⚠️ **CORS Test**
- OPTIONS method test expects 200 but gets 405
- Needs CORS middleware configuration in test setup

## Running Tests

```bash
# Install dependencies
pip install pytest pytest-asyncio httpx==0.24.1

# Run all tests
cd backend
python3 -m pytest test_main.py -v

# Run with coverage
python3 -m pytest test_main.py -v --cov=main --cov-report=html

# Run specific test
python3 -m pytest test_main.py::test_health_check -v
```

## Test Structure

### Fixtures
- `client` - TestClient with overridden database dependency
- `test_db` - In-memory SQLite database for each test
- `sample_aggregates` - Pre-populated daily aggregate data
- `sample_trips` - Pre-populated trip data
- `sample_zones` - Pre-populated taxi zone lookup data

### Test Database
- Uses in-memory SQLite instead of PostgreSQL for speed
- Creates materialized view tables (daily_trip_aggregates, trip_summary_view)
- Fresh database for each test (isolated)

## Test Categories

### 1. Health Check Tests
- Validates `/health` endpoint
- Checks database connectivity status
- Verifies environment information

### 2. Daily Aggregates Tests
- Tests `/api/aggregates/daily` endpoint
- Date range filtering (start_date, end_date)
- Trip type filtering (yellow, green, fhv, fhvhv)
- Limit parameter validation
- Response structure validation

### 3. Summary Tests
- Tests `/api/aggregates/summary` endpoint
- Grouped summary statistics by trip type
- Date range filtering

### 4. Trip Data Tests
- Tests `/api/trips` endpoint
- Pagination (page, page_size)
- Trip type filtering
- Date range filtering
- Response includes zone enrichment

### 5. Zone Lookup Tests
- Tests `/api/zones` endpoint
- Returns all taxi zones
- Includes borough, zone name, service zone

### 6. Error Handling Tests
- Invalid endpoints (404)
- Wrong HTTP methods (405)
- Parameter validation (422)
- CORS headers

### 7. Integration Tests
- Full workflow across multiple endpoints
- Validates end-to-end functionality

## Key Features

✨ **Isolated Test Database**
- Each test gets fresh SQLite database
- No interference between tests
- Fast execution (no network calls)

✨ **Comprehensive Coverage**
- All 5 main API endpoints tested
- Query parameter combinations
- Error cases and edge cases
- Response schema validation

✨ **Mocked Database**
- Uses TestClient with dependency override
- No actual PostgreSQL connection needed
- Sample data injected via fixtures

✨ **FastAPI TestClient**
- Uses Starlette's TestClient for synchronous testing
- Compatible with httpx 0.24.1
- No async/await complexity in tests

## Next Steps

### To Achieve 100% Pass Rate:

1. **Fix taxi_zone_lookup Table**
   ```python
   # Add to test_db fixture
   db.execute(text("""
       CREATE TABLE taxi_zone_lookup (
           location_id INTEGER PRIMARY KEY,
           borough TEXT,
           zone TEXT,
           service_zone TEXT
       )
   """))
   ```

2. **Adjust Expected Counts**
   - Update filter test assertions to match actual data
   - Or modify sample_aggregates/sample_trips to match expectations

3. **Fix CORS Test**
   - Add proper CORS middleware configuration
   - Or change test to expect 405 instead of 200

4. **Add Coverage Reporting**
   ```bash
   pip install pytest-cov
   pytest test_main.py --cov=main --cov-report=html
   ```

## Example Test Output

```
============================= test session starts ==============================
platform darwin -- Python 3.10.10, pytest-9.0.2, pluggy-1.6.0
collected 24 items

test_main.py::test_health_check PASSED                                   [  4%]
test_main.py::test_root_endpoint PASSED                                  [  8%]
test_main.py::test_items_endpoint PASSED                                 [ 12%]
...
======================== 15 passed, 6 failed, 3 errors in 1.48s ================
```

## Benefits

🎯 **Quality Assurance**
- Catch bugs before deployment
- Verify API contract compliance
- Ensure consistent behavior

🚀 **Development Speed**
- Fast feedback loop (< 2 seconds)
- No need to manually test endpoints
- Confidence in refactoring

📊 **Documentation**
- Tests serve as usage examples
- Show expected request/response formats
- Demonstrate error handling

## Notes

- Tests use in-memory SQLite, not production PostgreSQL
- Some SQL features differ between databases (materialized views simulated with tables)
- httpx version pinned to 0.24.1 for Starlette 0.35.1 compatibility
- Tests skip database startup event (create_schema_on_startup)
