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
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  // Highcharts reference
  Highcharts: typeof Highcharts = Highcharts;

  // Data properties
  aggregates: DailyAggregate[] = [];
  trips: Trip[] = [];
  
  // Filter properties
  startDate: string = '2021-01-01';
  endDate: string = '2025-12-01';
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
    
    let url = `${apiUrl}/api/aggregates/daily?start_date=${this.startDate}&end_date=${this.endDate}&limit=1000`;
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
      const typeAggregates = this.aggregates.filter(agg => agg.trip_type === type);
      if (typeAggregates.length === 0) return 0; // No data available
      
      const validDistanceAggregates = typeAggregates.filter(agg => agg.avg_trip_distance != null);
      if (validDistanceAggregates.length === 0) {
        // Trip type exists but has no distance data (like FHV)
        return 0;
      }
      
      const sum = validDistanceAggregates.reduce((s, agg) => s + (agg.avg_trip_distance || 0), 0);
      return sum / validDistanceAggregates.length;
    });

    // Track which types have no distance data
    const hasDistanceData = tripTypes.map(type => {
      const typeAggregates = this.aggregates.filter(agg => agg.trip_type === type);
      const validDistanceAggregates = typeAggregates.filter(agg => agg.avg_trip_distance != null);
      return validDistanceAggregates.length > 0;
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
          dataLabels: {
            enabled: true,
            formatter: function() {
              // @ts-ignore - accessing Highcharts point data
              const pointIndex = this.point.index;
              const yValue = this.y || 0;
              return hasDistanceData[pointIndex] ? yValue.toFixed(1) : 'N/A';
            },
            style: {
              color: '#c9d1d9',
              textOutline: 'none',
              fontSize: '11px'
            }
          }
        }
      },
      series: [{
        name: 'Avg Distance',
        type: 'column',
        data: avgDistanceData.map((value, index) => ({
          y: value,
          color: hasDistanceData[index] ? Object.values(colors)[index] : '#6b7280', // Gray for N/A values
          name: tripTypes[index].toUpperCase()
        }))
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
    this.endDate = '2025-12-01';
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
