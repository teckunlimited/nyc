import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { environment } from '../environments/environment';
import * as Highcharts from 'highcharts';
import { HighchartsChartModule } from 'highcharts-angular';

interface DailyAggregate {
  trip_date: string;
  trip_type: string;
  total_trips: number;
  total_revenue: number | null;
  avg_trip_distance: number | null;
  avg_trip_duration: number | null;
}

interface Trip {
  id: number;
  trip_type: string;
  pickup_datetime: string;
  dropoff_datetime: string;
  pickup_zone: string | null;
  dropoff_zone: string | null;
  trip_distance: number | null;
  total_amount: number | null;
  duration_minutes: number | null;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule, FormsModule, HighchartsChartModule],
  template: `
    <div class="dashboard">
      <!-- Header -->
      <header class="header">
        <div class="header-content">
          <h1>NYC TLC Analytics Dashboard</h1>
          <p class="subtitle">Real-time insights from millions of taxi trips</p>
        </div>
      </header>

      <!-- Filters Section -->
      <section class="filters-section">
        <div class="filter-container">
          <div class="filter-group">
            <label>Start Date</label>
            <input type="date" [(ngModel)]="startDate" (change)="loadAggregates()" />
          </div>
          <div class="filter-group">
            <label>End Date</label>
            <input type="date" [(ngModel)]="endDate" (change)="loadAggregates()" />
          </div>
          <div class="filter-group">
            <label>Trip Type</label>
            <select [(ngModel)]="selectedTripType" (change)="loadAggregates()">
              <option value="">All Types</option>
              <option value="yellow">Yellow Taxi</option>
              <option value="green">Green Taxi</option>
              <option value="fhv">FHV</option>
              <option value="fhvhv">FHVHV</option>
            </select>
          </div>
          <button (click)="resetFilters()" class="btn-reset">Reset Filters</button>
        </div>
      </section>

      <!-- KPI Cards -->
      <section class="kpi-section">
        <div class="kpi-grid">
          <div class="kpi-card" [class.skeleton]="loading">
            <div class="kpi-content" *ngIf="!loading">
              <div class="kpi-label">Total Trips</div>
              <div class="kpi-value">{{ totalTrips | number }}</div>
            </div>
            <div class="skeleton-content" *ngIf="loading">
              <div class="skeleton-text skeleton-label"></div>
              <div class="skeleton-text skeleton-value"></div>
            </div>
          </div>
          <div class="kpi-card" [class.skeleton]="loading">
            <div class="kpi-content" *ngIf="!loading">
              <div class="kpi-label">Total Revenue</div>
              <div class="kpi-value">{{ totalRevenue | currency }}</div>
            </div>
            <div class="skeleton-content" *ngIf="loading">
              <div class="skeleton-text skeleton-label"></div>
              <div class="skeleton-text skeleton-value"></div>
            </div>
          </div>
          <div class="kpi-card" [class.skeleton]="loading">
            <div class="kpi-content" *ngIf="!loading">
              <div class="kpi-label">Avg Distance</div>
              <div class="kpi-value">{{ avgDistance | number:'1.2-2' }} mi</div>
            </div>
            <div class="skeleton-content" *ngIf="loading">
              <div class="skeleton-text skeleton-label"></div>
              <div class="skeleton-text skeleton-value"></div>
            </div>
          </div>
          <div class="kpi-card" [class.skeleton]="loading">
            <div class="kpi-content" *ngIf="!loading">
              <div class="kpi-label">Avg Duration</div>
              <div class="kpi-value">{{ avgDuration | number:'1.0-0' }} min</div>
            </div>
            <div class="skeleton-content" *ngIf="loading">
              <div class="skeleton-text skeleton-label"></div>
              <div class="skeleton-text skeleton-value"></div>
            </div>
          </div>
        </div>
      </section>

      <!-- Charts Section -->
      <section class="charts-section">
        <div class="chart-row">
          <div class="chart-card">
            <h3>Daily Trips Volume</h3>
            <div class="chart-loader" *ngIf="loadingCharts">
              <div class="spinner"></div>
              <p>Loading chart data...</p>
            </div>
            <highcharts-chart
              *ngIf="tripsChartOptions && !loadingCharts"
              [Highcharts]="Highcharts"
              [options]="tripsChartOptions"
              style="width: 100%; height: 350px; display: block;"
            ></highcharts-chart>
          </div>
          <div class="chart-card">
            <h3>Revenue Trend</h3>
            <div class="chart-loader" *ngIf="loadingCharts">
              <div class="spinner"></div>
              <p>Loading chart data...</p>
            </div>
            <highcharts-chart
              *ngIf="revenueChartOptions && !loadingCharts"
              [Highcharts]="Highcharts"
              [options]="revenueChartOptions"
              style="width: 100%; height: 350px; display: block;"
            ></highcharts-chart>
          </div>
        </div>
        <div class="chart-row">
          <div class="chart-card">
            <h3>Trip Type Distribution</h3>
            <div class="chart-loader" *ngIf="loadingCharts">
              <div class="spinner"></div>
              <p>Loading chart data...</p>
            </div>
            <highcharts-chart
              *ngIf="pieChartOptions && !loadingCharts"
              [Highcharts]="Highcharts"
              [options]="pieChartOptions"
              style="width: 100%; height: 350px; display: block;"
            ></highcharts-chart>
          </div>
          <div class="chart-card">
            <h3>Average Distance by Type</h3>
            <div class="chart-loader" *ngIf="loadingCharts">
              <div class="spinner"></div>
              <p>Loading chart data...</p>
            </div>
            <highcharts-chart
              *ngIf="barChartOptions && !loadingCharts"
              [Highcharts]="Highcharts"
              [options]="barChartOptions"
              style="width: 100%; height: 350px; display: block;"
            ></highcharts-chart>
          </div>
        </div>
      </section>

      <!-- Data Table -->
      <section class="table-section">
        <h3>Daily Aggregates</h3>
        <div class="table-container" *ngIf="aggregates.length > 0; else noData">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Type</th>
                <th>Trips</th>
                <th>Revenue</th>
                <th>Avg Distance</th>
                <th>Avg Duration</th>
              </tr>
            </thead>
            <tbody>
              <tr *ngFor="let agg of paginatedAggregates">
                <td>{{ agg.trip_date | date:'MMM d, y' }}</td>
                <td><span class="badge" [attr.data-type]="agg.trip_type">{{ agg.trip_type }}</span></td>
                <td>{{ agg.total_trips | number }}</td>
                <td>{{ agg.total_revenue | currency }}</td>
                <td>{{ agg.avg_trip_distance | number:'1.2-2' }} mi</td>
                <td>{{ agg.avg_trip_duration | number:'1.0-0' }} min</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="pagination-controls" *ngIf="aggregates.length > 0">
          <button (click)="prevAggregatesPage()" [disabled]="currentAggregatesPage === 1" class="btn-reset">Previous</button>
          <span>Page {{ currentAggregatesPage }} of {{ totalAggregatesPages }}</span>
          <button (click)="nextAggregatesPage()" [disabled]="currentAggregatesPage >= totalAggregatesPages" class="btn-reset">Next</button>
        </div>
        <ng-template #noData>
          <div class="no-data">
            <p>{{ loading ? 'Loading data...' : 'No data available for selected filters' }}</p>
          </div>
        </ng-template>
      </section>
    </div>
  `,
  styles: [`
    /* Global Styles */
    :host {
      display: block;
      min-height: 100vh;
      background: #0d1117;
      color: #c9d1d9;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
    }

    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    /* Dashboard Container */
    .dashboard {
      min-height: 100vh;
      background: #0d1117;
      padding: 0;
    }

    /* Header */
    .header {
      background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
      border-bottom: 1px solid #30363d;
      padding: 2rem 3rem;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }

    .header-content h1 {
      font-size: 2rem;
      font-weight: 700;
      color: #58a6ff;
      margin-bottom: 0.5rem;
    }

    .subtitle {
      color: #8b949e;
      font-size: 1rem;
    }

    /* Filters Section */
    .filters-section {
      background: #161b22;
      border-bottom: 1px solid #30363d;
      padding: 1.5rem 3rem;
    }

    .filter-container {
      display: flex;
      gap: 1.5rem;
      align-items: flex-end;
      flex-wrap: wrap;
    }

    .filter-group {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }

    .filter-group label {
      color: #8b949e;
      font-size: 0.875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .filter-group input,
    .filter-group select {
      background: #0d1117;
      border: 1px solid #30363d;
      color: #c9d1d9;
      padding: 0.5rem 0.75rem;
      border-radius: 6px;
      font-size: 0.875rem;
      min-width: 150px;
      transition: all 0.2s;
    }

    .filter-group input:focus,
    .filter-group select:focus {
      outline: none;
      border-color: #58a6ff;
      box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.1);
    }

    .btn-reset {
      background: #21262d;
      border: 1px solid #30363d;
      color: #c9d1d9;
      padding: 0.5rem 1.5rem;
      border-radius: 6px;
      font-size: 0.875rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s;
    }

    .btn-reset:hover {
      background: #30363d;
      border-color: #58a6ff;
    }

    /* KPI Section */
    .kpi-section {
      padding: 2rem 3rem;
    }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 1.5rem;
    }

    .kpi-card {
      background: linear-gradient(135deg, #161b22 0%, #1c2128 100%);
      border: 1px solid #30363d;
      border-radius: 12px;
      padding: 1.5rem;
      transition: all 0.3s;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }

    .kpi-card:hover {
      border-color: #58a6ff;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(88, 166, 255, 0.2);
    }

    .kpi-content {
      width: 100%;
    }

    .kpi-label {
      color: #8b949e;
      font-size: 0.875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 0.5rem;
    }

    .kpi-value {
      color: #c9d1d9;
      font-size: 1.75rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
    }

    .kpi-change {
      font-size: 0.75rem;
      font-weight: 600;
    }

    .kpi-change.positive {
      color: #3fb950;
    }

    .kpi-change.negative {
      color: #f85149;
    }

    /* Charts Section */
    .charts-section {
      padding: 0 3rem 2rem 3rem;
    }

    .chart-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
      gap: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .chart-card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
      padding: 1.5rem;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }

    .chart-card h3 {
      color: #c9d1d9;
      font-size: 1.125rem;
      font-weight: 600;
      margin-bottom: 1rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid #30363d;
    }

    /* Table Section */
    .table-section {
      padding: 0 3rem 3rem 3rem;
    }

    .table-section h3 {
      color: #c9d1d9;
      font-size: 1.25rem;
      font-weight: 600;
      margin-bottom: 1rem;
    }

    .pagination-controls {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 1rem;
      padding: 1rem 0;
    }

    .pagination-controls button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .pagination-controls span {
      color: #c9d1d9;
      font-size: 0.875rem;
    }

    .table-container {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    thead {
      background: #1c2128;
    }

    th {
      color: #8b949e;
      font-size: 0.875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      padding: 1rem;
      text-align: left;
      border-bottom: 1px solid #30363d;
    }

    td {
      color: #c9d1d9;
      padding: 1rem;
      border-bottom: 1px solid #21262d;
    }

    tbody tr {
      transition: background 0.2s;
    }

    tbody tr:hover {
      background: #1c2128;
    }

    .badge {
      display: inline-block;
      padding: 0.25rem 0.75rem;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .badge[data-type="yellow"] {
      background: rgba(251, 191, 36, 0.2);
      color: #fbbf24;
    }

    .badge[data-type="green"] {
      background: rgba(34, 197, 94, 0.2);
      color: #22c55e;
    }

    .badge[data-type="fhv"] {
      background: rgba(147, 51, 234, 0.2);
      color: #9333ea;
    }

    .badge[data-type="fhvhv"] {
      background: rgba(59, 130, 246, 0.2);
      color: #3b82f6;
    }

    .no-data {
      padding: 3rem;
      text-align: center;
      color: #8b949e;
      font-size: 1rem;
    }

    /* Loading Skeleton Styles */
    .skeleton {
      position: relative;
      overflow: hidden;
    }

    .skeleton-content {
      padding: 1rem;
    }

    .skeleton-text {
      background: linear-gradient(90deg, #21262d 25%, #30363d 50%, #21262d 75%);
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite;
      border-radius: 4px;
      height: 20px;
      margin-bottom: 0.75rem;
    }

    .skeleton-label {
      width: 60%;
      height: 16px;
    }

    .skeleton-value {
      width: 80%;
      height: 32px;
      margin-bottom: 0;
    }

    @keyframes shimmer {
      0% {
        background-position: 200% 0;
      }
      100% {
        background-position: -200% 0;
      }
    }

    /* Chart Loader */
    .chart-loader {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 350px;
      gap: 1rem;
    }

    .chart-loader p {
      color: #8b949e;
      font-size: 0.875rem;
    }

    /* Spinner Animation */
    .spinner {
      width: 40px;
      height: 40px;
      border: 4px solid #21262d;
      border-top: 4px solid #58a6ff;
      border-radius: 50%;
      animation: spin 1s linear infinite;
    }

    @keyframes spin {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    /* Fade-in animation for loaded content */
    .kpi-card:not(.skeleton) .kpi-content {
      animation: fadeIn 0.3s ease-in;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(10px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    /* Responsive */
    @media (max-width: 1024px) {
      .chart-row {
        grid-template-columns: 1fr;
      }
      
      .header,
      .filters-section,
      .kpi-section,
      .charts-section,
      .table-section {
        padding-left: 1.5rem;
        padding-right: 1.5rem;
      }
    }
  `]
})
export class AppComponent implements OnInit {
  // Highcharts reference
  Highcharts: typeof Highcharts = Highcharts;

  // Data properties
  aggregates: DailyAggregate[] = [];
  trips: Trip[] = [];
  
  // Filter properties
  startDate: string = '2021-01-01';
  endDate: string = '2021-02-01';
  selectedTripType: string = '';
  
  // Pagination for trips
  currentPage = 1;
  totalPages = 1;
  pageSize = 20;
  
  // Pagination for aggregates
  currentAggregatesPage = 1;
  aggregatesPageSize = 20;
  
  // Loading states (granular for better UX)
  loading = false;
  loadingCharts = false;
  loadingTrips = false;
  
  // Computed statistics
  totalTrips = 0;
  totalRevenue = 0;
  avgDistance = 0;
  avgDuration = 0;

  // Chart options
  tripsChartOptions?: Highcharts.Options;
  revenueChartOptions?: Highcharts.Options;
  pieChartOptions?: Highcharts.Options;
  barChartOptions?: Highcharts.Options;

  constructor(private http: HttpClient, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    console.log('Component initialized');
    console.log('Highcharts available:', typeof Highcharts !== 'undefined');
    this.loadAggregates();
    this.loadTrips();
  }

  loadAggregates() {
    this.loading = true;
    this.loadingCharts = true;
    const apiUrl = environment.apiUrl || 'http://localhost:8000';
    
    let url = `${apiUrl}/api/aggregates/daily?start_date=${this.startDate}&end_date=${this.endDate}&limit=500`;
    if (this.selectedTripType) {
      url += `&trip_type=${this.selectedTripType}`;
    }

    this.http.get<{ data: DailyAggregate[], total: number }>(url)
      .subscribe({
        next: (response) => {
          console.log('Loaded aggregates:', response.data.length, 'records');
          this.aggregates = response.data;
          this.currentAggregatesPage = 1;
          
          // Calculate stats immediately for faster KPI display
          this.calculateStatistics();
          this.loading = false;
          
          // Update charts after a slight delay for perceived performance
          setTimeout(() => {
            this.updateCharts();
            this.loadingCharts = false;
          }, 100);
        },
        error: (error) => {
          console.error('Error loading aggregates:', error);
          this.loading = false;
          this.loadingCharts = false;
        }
      });
  }

  loadTrips() {
    this.loadingTrips = true;
    const apiUrl = environment.apiUrl || 'http://localhost:8000';
    
    let url = `${apiUrl}/api/trips?page=${this.currentPage}&page_size=${this.pageSize}`;
    if (this.selectedTripType) {
      url += `&trip_type=${this.selectedTripType}`;
    }

    this.http.get<{ data: Trip[], total: number, page: number, page_size: number }>(url)
      .subscribe({
        next: (response) => {
          this.trips = response.data;
          this.totalPages = Math.ceil(response.total / response.page_size);
          this.loadingTrips = false;
        },
        error: (error) => {
          console.error('Error loading trips:', error);
          this.loadingTrips = false;
        }
      });
  }

  calculateStatistics() {
    if (this.aggregates.length === 0) {
      this.totalTrips = 0;
      this.totalRevenue = 0;
      this.avgDistance = 0;
      this.avgDuration = 0;
      return;
    }

    this.totalTrips = this.aggregates.reduce((sum, agg) => sum + agg.total_trips, 0);
    this.totalRevenue = this.aggregates.reduce((sum, agg) => sum + (agg.total_revenue || 0), 0);
    
    const validDistances = this.aggregates.filter(agg => agg.avg_trip_distance != null);
    this.avgDistance = validDistances.length > 0
      ? validDistances.reduce((sum, agg) => sum + (agg.avg_trip_distance || 0), 0) / validDistances.length
      : 0;
    
    const validDurations = this.aggregates.filter(agg => agg.avg_trip_duration != null);
    this.avgDuration = validDurations.length > 0
      ? validDurations.reduce((sum, agg) => sum + (agg.avg_trip_duration || 0), 0) / validDurations.length
      : 0;
  }

  updateCharts() {
    console.log('updateCharts called with', this.aggregates.length, 'aggregates');
    
    if (this.aggregates.length === 0) {
      console.log('No aggregates to display');
      return;
    }
    
    // Group data by date and trip type
    const dateMap = new Map<string, Map<string, DailyAggregate>>();
    
    this.aggregates.forEach(agg => {
      if (!dateMap.has(agg.trip_date)) {
        dateMap.set(agg.trip_date, new Map());
      }
      dateMap.get(agg.trip_date)!.set(agg.trip_type, agg);
    });

    const dates = Array.from(dateMap.keys()).sort();
    console.log('Processing', dates.length, 'dates');
    
    const tripTypes = ['yellow', 'green', 'fhv', 'fhvhv'];
    const colors = {
      yellow: '#fbbf24',
      green: '#22c55e',
      fhv: '#9333ea',
      fhvhv: '#3b82f6'
    };

    // Trips Volume Chart
    const tripsSeries = tripTypes.map(type => ({
      name: type.toUpperCase(),
      data: dates.map(date => {
        const typeData = dateMap.get(date)?.get(type);
        return typeData ? typeData.total_trips : 0;
      }),
      color: colors[type as keyof typeof colors]
    }));

    console.log('Trips series data:', tripsSeries);

    this.tripsChartOptions = {
      chart: {
        type: 'line',
        backgroundColor: 'transparent',
        height: 350,
        style: {
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
        }
      },
      title: {
        text: '',
        style: { color: '#c9d1d9' }
      },
      xAxis: {
        categories: dates.map(d => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })),
        labels: {
          style: { color: '#8b949e' },
          rotation: -45
        },
        gridLineColor: '#30363d',
        lineColor: '#30363d'
      },
      yAxis: {
        title: {
          text: 'Number of Trips',
          style: { color: '#8b949e' }
        },
        labels: {
          style: { color: '#8b949e' }
        },
        gridLineColor: '#30363d'
      },
      legend: {
        itemStyle: { color: '#c9d1d9' },
        itemHoverStyle: { color: '#58a6ff' }
      },
      plotOptions: {
        line: {
          marker: {
            enabled: false
          }
        }
      },
      series: tripsSeries as any,
      credits: {
        enabled: false
      }
    };

    // Revenue Chart
    const revenueSeries = tripTypes.map(type => ({
      name: type.toUpperCase(),
      data: dates.map(date => {
        const typeData = dateMap.get(date)?.get(type);
        return typeData ? (typeData.total_revenue || 0) : 0;
      }),
      color: colors[type as keyof typeof colors]
    }));

    this.revenueChartOptions = {
      chart: {
        type: 'area',
        backgroundColor: 'transparent',
        height: 350,
        style: {
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
        }
      },
      title: {
        text: '',
        style: { color: '#c9d1d9' }
      },
      xAxis: {
        categories: dates.map(d => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })),
        labels: {
          style: { color: '#8b949e' },
          rotation: -45
        },
        gridLineColor: '#30363d',
        lineColor: '#30363d'
      },
      yAxis: {
        title: {
          text: 'Revenue ($)',
          style: { color: '#8b949e' }
        },
        labels: {
          style: { color: '#8b949e' }
        },
        gridLineColor: '#30363d'
      },
      legend: {
        itemStyle: { color: '#c9d1d9' },
        itemHoverStyle: { color: '#58a6ff' }
      },
      plotOptions: {
        area: {
          stacking: 'normal' as const,
          marker: {
            enabled: false
          },
          fillOpacity: 0.3
        }
      },
      series: revenueSeries as any,
      credits: {
        enabled: false
      }
    };

    // Pie Chart - Trip Type Distribution
    const tripTypeTotals = tripTypes.map(type => {
      const total = dates.reduce((sum, date) => {
        const typeData = dateMap.get(date)?.get(type);
        return sum + (typeData ? typeData.total_trips : 0);
      }, 0);
      return {
        name: type.toUpperCase(),
        y: total,
        color: colors[type as keyof typeof colors]
      };
    }).filter(item => item.y > 0);

    this.pieChartOptions = {
      chart: {
        type: 'pie',
        backgroundColor: 'transparent',
        height: 350,
        style: {
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
        }
      },
      title: {
        text: '',
        style: { color: '#c9d1d9' }
      },
      plotOptions: {
        pie: {
          allowPointSelect: true,
          cursor: 'pointer',
          dataLabels: {
            enabled: true,
            format: '<b>{point.name}</b>: {point.percentage:.1f}%',
            style: {
              color: '#c9d1d9',
              textOutline: 'none'
            }
          },
          showInLegend: true
        }
      },
      legend: {
        itemStyle: { color: '#c9d1d9' },
        itemHoverStyle: { color: '#58a6ff' }
      },
      series: [{
        name: 'Trips',
        type: 'pie',
        data: tripTypeTotals
      }],
      credits: {
        enabled: false
      }
    };

    // Bar Chart - Average Distance by Type
    const avgDistanceData = tripTypes.map(type => {
      const typeAggregates = this.aggregates.filter(agg => agg.trip_type === type && agg.avg_trip_distance != null);
      if (typeAggregates.length === 0) return 0;
      const sum = typeAggregates.reduce((s, agg) => s + (agg.avg_trip_distance || 0), 0);
      return sum / typeAggregates.length;
    });

    this.barChartOptions = {
      chart: {
        type: 'column',
        backgroundColor: 'transparent',
        height: 350,
        style: {
          fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
        }
      },
      title: {
        text: '',
        style: { color: '#c9d1d9' }
      },
      xAxis: {
        categories: tripTypes.map(t => t.toUpperCase()),
        labels: {
          style: { color: '#8b949e' }
        },
        gridLineColor: '#30363d',
        lineColor: '#30363d'
      },
      yAxis: {
        title: {
          text: 'Miles',
          style: { color: '#8b949e' }
        },
        labels: {
          style: { color: '#8b949e' }
        },
        gridLineColor: '#30363d'
      },
      legend: {
        enabled: false
      },
      plotOptions: {
        column: {
          colorByPoint: true,
          colors: Object.values(colors)
        }
      },
      series: [{
        name: 'Avg Distance',
        type: 'column',
        data: avgDistanceData
      }],
      credits: {
        enabled: false
      }
    };
    
    console.log('Charts updated successfully');
    
    // Force change detection for charts
    this.cdr.detectChanges();
  }

  get paginatedAggregates(): DailyAggregate[] {
    const start = (this.currentAggregatesPage - 1) * this.aggregatesPageSize;
    const end = start + this.aggregatesPageSize;
    return this.aggregates.slice(start, end);
  }

  get totalAggregatesPages(): number {
    return Math.ceil(this.aggregates.length / this.aggregatesPageSize);
  }

  nextAggregatesPage() {
    if (this.currentAggregatesPage < this.totalAggregatesPages) {
      this.currentAggregatesPage++;
    }
  }

  prevAggregatesPage() {
    if (this.currentAggregatesPage > 1) {
      this.currentAggregatesPage--;
    }
  }

  resetFilters() {
    this.startDate = '2021-01-01';
    this.endDate = '2021-02-01';
    this.selectedTripType = '';
    this.currentAggregatesPage = 1;
    this.loadAggregates();
    this.loadTrips();
  }

  nextPage() {
    if (this.currentPage < this.totalPages) {
      this.currentPage++;
      this.loadTrips();
    }
  }

  prevPage() {
    if (this.currentPage > 1) {
      this.currentPage--;
      this.loadTrips();
    }
  }
}
