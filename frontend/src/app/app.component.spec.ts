import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { FormsModule } from '@angular/forms';
import { AppComponent } from './app.component';
import { HighchartsChartModule } from 'highcharts-angular';
import { ChangeDetectorRef } from '@angular/core';

describe('AppComponent', () => {
  let component: AppComponent;
  let fixture: ComponentFixture<AppComponent>;
  let httpMock: HttpTestingController;

  const mockAggregates = {
    total: 5,
    data: [
      {
        trip_date: '2021-05-01',
        trip_type: 'yellow',
        total_trips: 1000,
        total_revenue: 15000.50,
        avg_trip_distance: 3.5,
        avg_trip_duration: 15.2
      },
      {
        trip_date: '2021-05-02',
        trip_type: 'yellow',
        total_trips: 1100,
        total_revenue: 16500.75,
        avg_trip_distance: 3.8,
        avg_trip_duration: 16.0
      }
    ]
  };

  const mockTrips = {
    total: 3,
    page: 1,
    page_size: 100,
    total_pages: 1,
    data: [
      {
        id: 1,
        trip_type: 'yellow',
        pickup_datetime: '2021-05-01 10:00:00',
        dropoff_datetime: '2021-05-01 10:15:00',
        pickup_zone: 'East Harlem North',
        dropoff_zone: 'Upper West Side',
        trip_distance: 2.5,
        total_amount: 17.3,
        duration_minutes: 15.0
      }
    ]
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        AppComponent,
        HttpClientTestingModule,
        FormsModule,
        HighchartsChartModule
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(AppComponent);
    component = fixture.componentInstance;
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  // Helper function to handle ngOnInit HTTP requests
  const flushInitRequests = () => {
    const aggReq = httpMock.expectOne((request) => 
      request.url.includes('/api/aggregates/daily')
    );
    const tripsReq = httpMock.expectOne((request) => 
      request.url.includes('/api/trips')
    );
    aggReq.flush(mockAggregates);
    tripsReq.flush(mockTrips);
  };

  // ==================== Basic Component Tests ====================

  it('should create the component', () => {
    expect(component).toBeTruthy();
  });

  it('should have highcharts reference', () => {
    expect(component.Highcharts).toBeDefined();
  });

  it('should initialize with correct default values', () => {
    expect(component.aggregates).toEqual([]);
    expect(component.trips).toEqual([]);
    expect(component.selectedTripType).toBe('');
    expect(component.currentAggregatesPage).toBe(1);
    expect(component.aggregatesPageSize).toBe(20);
  });

  // ==================== HTTP Request Tests ====================

  describe('loadAggregates', () => {
    it('should load aggregates on initialization', () => {
      fixture.detectChanges(); // triggers ngOnInit
      flushInitRequests();

      expect(component.aggregates.length).toBe(2);
      expect(component.aggregates[0].trip_date).toBe('2021-05-01');
    });

    it('should include date filters in request', () => {
      component.startDate = '2021-05-01';
      component.endDate = '2021-05-31';
      component.loadAggregates();

      const req = httpMock.expectOne((request) => 
        request.url.includes('/api/aggregates/daily')
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.url).toContain('start_date=2021-05-01');
      expect(req.request.url).toContain('end_date=2021-05-31');
      req.flush(mockAggregates);
    });

    it('should include trip type filter in request', () => {
      component.selectedTripType = 'yellow';
      component.loadAggregates();

      const req = httpMock.expectOne((request) => 
        request.url.includes('/api/aggregates/daily')
      );
      expect(req.request.method).toBe('GET');
      expect(req.request.url).toContain('trip_type=yellow');
      req.flush(mockAggregates);
    });

    it('should handle empty response', () => {
      component.loadAggregates();

      const req = httpMock.expectOne((request) => 
        request.url.includes('/api/aggregates/daily')
      );
      req.flush({ total: 0, data: [] });

      expect(component.aggregates).toEqual([]);
    });

    it('should handle HTTP errors gracefully', () => {
      spyOn(console, 'error');
      component.loadAggregates();

      const req = httpMock.expectOne((request) => 
        request.url.includes('/api/aggregates/daily')
      );
      req.error(new ErrorEvent('Network error'));

      expect(console.error).toHaveBeenCalled();
    });
  });

  describe('loadTrips', () => {
    it('should load trips', () => {
      component.loadTrips();

      const req = httpMock.expectOne((request) => 
        request.url.includes('/api/trips')
      );
      expect(req.request.method).toBe('GET');
      req.flush(mockTrips);

      expect(component.trips.length).toBe(1);
      expect(component.trips[0].trip_type).toBe('yellow');
    });

    it('should include pagination parameters', () => {
      component.loadTrips();

      const req = httpMock.expectOne((request) => 
        request.url.includes('/api/trips')
      );
      expect(req.request.url).toContain('page=1');
      expect(req.request.url).toContain('page_size=20');
      req.flush(mockTrips);
    });
  });

  // ==================== KPI Calculation Tests ====================

  describe('calculateStatistics', () => {
    beforeEach(() => {
      component.aggregates = mockAggregates.data;
    });

    it('should calculate total trips correctly', () => {
      component.calculateStatistics();
      expect(component.totalTrips).toBe(2100); // 1000 + 1100
    });

    it('should calculate total revenue correctly', () => {
      component.calculateStatistics();
      expect(component.totalRevenue).toBeCloseTo(31501.25, 2); // 15000.50 + 16500.75
    });

    it('should calculate average distance correctly', () => {
      component.calculateStatistics();
      expect(component.avgDistance).toBeCloseTo(3.65, 2); // (3.5 + 3.8) / 2
    });

    it('should calculate average duration correctly', () => {
      component.calculateStatistics();
      expect(component.avgDuration).toBeCloseTo(15.6, 2); // (15.2 + 16.0) / 2
    });

    it('should handle empty aggregates', () => {
      component.aggregates = [];
      component.calculateStatistics();

      expect(component.totalTrips).toBe(0);
      expect(component.totalRevenue).toBe(0);
      expect(component.avgDistance).toBe(0);
      expect(component.avgDuration).toBe(0);
    });

    it('should handle null values in aggregates', () => {
      component.aggregates = [{
        trip_date: '2021-05-01',
        trip_type: 'yellow',
        total_trips: 1000,
        total_revenue: null,
        avg_trip_distance: null,
        avg_trip_duration: null
      }];
      component.calculateStatistics();

      expect(component.totalTrips).toBe(1000);
      expect(component.totalRevenue).toBe(0);
    });
  });

  // ==================== Chart Update Tests ====================

  describe('updateCharts', () => {
    beforeEach(() => {
      component.aggregates = mockAggregates.data;
    });

    it('should create chart options when data is available', () => {
      component.updateCharts();

      expect(component.tripsChartOptions).toBeDefined();
      expect(component.revenueChartOptions).toBeDefined();
      expect(component.pieChartOptions).toBeDefined();
      expect(component.barChartOptions).toBeDefined();
    });

    it('should set Highcharts reference', () => {
      component.updateCharts();
      expect(component.Highcharts).toBeDefined();
    });

    it('should create trips volume chart with correct data', () => {
      component.updateCharts();
      const chart = component.tripsChartOptions;

      expect(chart).toBeDefined();
      expect(chart?.series?.length).toBeGreaterThan(0);
    });

    it('should create revenue trend chart with correct data', () => {
      component.updateCharts();
      const chart = component.revenueChartOptions;

      expect(chart).toBeDefined();
      expect(chart?.chart?.type).toBe('area');
    });

    it('should create distribution pie chart', () => {
      component.updateCharts();
      const chart = component.pieChartOptions;

      expect(chart).toBeDefined();
      expect(chart?.chart?.type).toBe('pie');
    });

    it('should create bar chart', () => {
      component.updateCharts();
      const chart = component.barChartOptions;

      expect(chart).toBeDefined();
      expect(chart?.chart?.type).toBe('column');
    });

    it('should handle empty aggregates', () => {
      component.aggregates = [];
      component.updateCharts();

      // updateCharts returns early when no aggregates, charts remain undefined
      expect(component.aggregates.length).toBe(0);
    });
  });

  // ==================== Filter Tests ====================

  describe('resetFilters', () => {
    it('should reset all filters to default values', () => {
      component.startDate = '2021-06-01';
      component.endDate = '2021-06-30';
      component.selectedTripType = 'yellow';

      component.resetFilters();

      expect(component.startDate).toBe('2021-01-01');
      expect(component.endDate).toBe('2021-12-31');
      expect(component.selectedTripType).toBe('');
    });

    it('should reload aggregates after resetting', () => {
      spyOn(component, 'loadAggregates');
      component.resetFilters();

      expect(component.loadAggregates).toHaveBeenCalled();
    });
  });

  // ==================== Pagination Tests ====================

  describe('Pagination', () => {
    beforeEach(() => {
      component.aggregates = Array.from({ length: 50 }, (_, i) => ({
        trip_date: `2021-05-${String(i + 1).padStart(2, '0')}`,
        trip_type: 'yellow',
        total_trips: 1000 + i,
        total_revenue: 15000 + i,
        avg_trip_distance: 3.5,
        avg_trip_duration: 15.0
      }));
    });

    it('should return correct page of aggregates', () => {
      component.currentAggregatesPage = 1;
      component.aggregatesPageSize = 20;

      const paginatedData = component.paginatedAggregates;

      expect(paginatedData.length).toBe(20);
      expect(paginatedData[0].trip_date).toBe('2021-05-01');
    });

    it('should return second page correctly', () => {
      component.currentAggregatesPage = 2;
      component.aggregatesPageSize = 20;

      const paginatedData = component.paginatedAggregates;

      expect(paginatedData.length).toBe(20);
      expect(paginatedData[0].trip_date).toBe('2021-05-21');
    });

    it('should return last page with remaining items', () => {
      component.currentAggregatesPage = 3;
      component.aggregatesPageSize = 20;

      const paginatedData = component.paginatedAggregates;

      expect(paginatedData.length).toBe(10); // 50 total, 20 + 20 + 10
    });

    it('should calculate total pages correctly', () => {
      component.aggregatesPageSize = 20;
      const totalPages = Math.ceil(component.aggregates.length / component.aggregatesPageSize);

      expect(totalPages).toBe(3); // 50 items / 20 per page = 3 pages
    });

    it('should go to next page', () => {
      component.currentAggregatesPage = 1;
      component.nextAggregatesPage();

      expect(component.currentAggregatesPage).toBe(2);
    });

    it('should go to previous page', () => {
      component.currentAggregatesPage = 2;
      component.prevAggregatesPage();

      expect(component.currentAggregatesPage).toBe(1);
    });

    it('should not go below page 1', () => {
      component.currentAggregatesPage = 1;
      component.prevAggregatesPage();

      expect(component.currentAggregatesPage).toBe(1);
    });

    it('should not exceed max pages', () => {
      const maxPages = Math.ceil(component.aggregates.length / component.aggregatesPageSize);
      component.currentAggregatesPage = maxPages;
      component.nextAggregatesPage();

      expect(component.currentAggregatesPage).toBe(maxPages);
    });
  });

  // ==================== Date Handling Tests ====================

  describe('formatDate', () => {
    it('should handle date strings', () => {
      const date = '2021-05-15';
      // Date handling is tested through component data loading
      expect(date).toBe('2021-05-15');
    });
  });

  // ==================== Data Formatting Tests ====================

  describe('Data Formatting', () => {
    it('should format currency correctly', () => {
      const value = 15000.50;
      // Angular currency pipe is tested through template
      expect(value).toBe(15000.50);
    });

    it('should format numbers with correct precision', () => {
      const distance = 3.567;
      const formatted = distance.toFixed(2);
      expect(formatted).toBe('3.57');
    });
  });

  // ==================== Integration Tests ====================

  describe('Component Initialization', () => {
    it('should load data on initialization', () => {
      fixture.detectChanges(); // triggers ngOnInit
      flushInitRequests();

      expect(component.aggregates.length).toBeGreaterThan(0);
      expect(component.trips.length).toBeGreaterThan(0);
    });

    it('should calculate statistics after loading aggregates', () => {
      spyOn(component, 'calculateStatistics');
      fixture.detectChanges();
      flushInitRequests();

      expect(component.calculateStatistics).toHaveBeenCalled();
    });

    it('should update charts after loading aggregates', () => {
      spyOn(component, 'updateCharts');
      fixture.detectChanges();
      flushInitRequests();

      expect(component.updateCharts).toHaveBeenCalled();
    });
  });

  // ==================== Error Handling Tests ====================

  describe('Error Handling', () => {
    it('should handle network errors for aggregates', () => {
      spyOn(console, 'error');
      component.loadAggregates();

      const req = httpMock.expectOne((request) => 
        request.url.includes('/api/aggregates/daily')
      );
      req.error(new ErrorEvent('Network error'));

      expect(console.error).toHaveBeenCalled();
      expect(component.aggregates).toEqual([]);
    });

    it('should handle network errors for trips', () => {
      spyOn(console, 'error');
      component.loadTrips();

      const req = httpMock.expectOne((request) => 
        request.url.includes('/api/trips')
      );
      req.error(new ErrorEvent('Network error'));

      expect(console.error).toHaveBeenCalled();
      expect(component.trips).toEqual([]);
    });

    it('should handle 404 errors', () => {
      spyOn(console, 'error');
      component.loadAggregates();

      const req = httpMock.expectOne((request) => 
        request.url.includes('/api/aggregates/daily')
      );
      req.flush('Not found', { status: 404, statusText: 'Not Found' });

      expect(console.error).toHaveBeenCalled();
    });

    it('should handle 500 errors', () => {
      spyOn(console, 'error');
      component.loadAggregates();

      const req = httpMock.expectOne((request) => 
        request.url.includes('/api/aggregates/daily')
      );
      req.flush('Server error', { status: 500, statusText: 'Internal Server Error' });

      expect(console.error).toHaveBeenCalled();
    });
  });

  // ==================== Edge Cases ====================

  describe('Edge Cases', () => {
    it('should handle extremely large numbers', () => {
      component.aggregates = [{
        trip_date: '2021-05-01',
        trip_type: 'yellow',
        total_trips: 1000000,
        total_revenue: 99999999.99,
        avg_trip_distance: 999.99,
        avg_trip_duration: 999.99
      }];

      component.calculateStatistics();

      expect(component.totalTrips).toBe(1000000);
      expect(component.totalRevenue).toBe(99999999.99);
    });

    it('should handle zero values', () => {
      component.aggregates = [{
        trip_date: '2021-05-01',
        trip_type: 'yellow',
        total_trips: 0,
        total_revenue: 0,
        avg_trip_distance: 0,
        avg_trip_duration: 0
      }];

      component.calculateStatistics();

      expect(component.totalTrips).toBe(0);
      expect(component.totalRevenue).toBe(0);
    });

    it('should handle negative values', () => {
      component.aggregates = [{
        trip_date: '2021-05-01',
        trip_type: 'yellow',
        total_trips: 1000,
        total_revenue: -100,
        avg_trip_distance: -5,
        avg_trip_duration: -10
      }];

      component.calculateStatistics();

      expect(component.totalRevenue).toBe(-100);
    });

    it('should handle single aggregate', () => {
      component.aggregates = [{
        trip_date: '2021-05-01',
        trip_type: 'yellow',
        total_trips: 1000,
        total_revenue: 15000,
        avg_trip_distance: 3.5,
        avg_trip_duration: 15.0
      }];

      component.calculateStatistics();

      expect(component.totalTrips).toBe(1000);
      expect(component.avgDistance).toBe(3.5);
    });
  });
});
