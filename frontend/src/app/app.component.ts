import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { environment } from '../environments/environment';
import { Chart, registerables } from 'chart.js';

// Register Chart.js components
Chart.register(...registerables);

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
  imports: [CommonModule, HttpClientModule, FormsModule],
  template: `
    <div class="container">
      <header>
        <h1>🚕 NYC TLC Trip Data Analytics</h1>
        <p>Real-time analytics from millions of NYC taxi trips</p>
      </header>

      <main>
        <!-- Date Filter Section -->
        <section class="filters">
          <h2>📅 Filter Data</h2>
          <div class="filter-group">
            <div class="filter-item">
              <label>Start Date:</label>
              <input type="date" [(ngModel)]="startDate" (change)="loadAggregates()" />
            </div>
            <div class="filter-item">
              <label>End Date:</label>
              <input type="date" [(ngModel)]="endDate" (change)="loadAggregates()" />
            </div>
            <div class="filter-item">
              <label>Trip Type:</label>
              <select [(ngModel)]="selectedTripType" (change)="loadAggregates()">
                <option value="">All Types</option>
                <option value="yellow">Yellow Taxi</option>
                <option value="green">Green Taxi</option>
                <option value="fhv">FHV</option>
                <option value="fhvhv">FHVHV</option>
              </select>
            </div>
            <button (click)="resetFilters()" class="btn-secondary">Reset</button>
          </div>
        </section>

        <!-- Time Series Chart -->
        <section class="chart-section">
          <h2>📊 Daily Trips Time Series</h2>
          <div class="chart-container">
            <canvas id="tripsChart"></canvas>
          </div>
        </section>

        <!-- Revenue Chart -->
        <section class="chart-section">
          <h2>💰 Daily Revenue Time Series</h2>
          <div class="chart-container">
            <canvas id="revenueChart"></canvas>
          </div>
        </section>

        <!-- Summary Statistics -->
        <section class="stats-grid">
          <div class="stat-card">
            <h3>Total Trips</h3>
            <p class="stat-value">{{ totalTrips | number }}</p>
          </div>
          <div class="stat-card">
            <h3>Total Revenue</h3>
            <p class="stat-value">{{ totalRevenue | currency }}</p>
          </div>
          <div class="stat-card">
            <h3>Avg Distance</h3>
            <p class="stat-value">{{ avgDistance | number:'1.2-2' }} mi</p>
          </div>
          <div class="stat-card">
            <h3>Avg Duration</h3>
            <p class="stat-value">{{ avgDuration | number:'1.0-0' }} min</p>
          </div>
        </section>

        <!-- Aggregates Table -->
        <section class="data-table">
          <h2>📋 Daily Aggregates Table</h2>
          <div class="table-container">
            <table *ngIf="aggregates.length > 0; else noData">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Trip Type</th>
                  <th>Total Trips</th>
                  <th>Revenue</th>
                  <th>Avg Distance</th>
                  <th>Avg Duration</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let agg of aggregates">
                  <td>{{ agg.trip_date | date:'shortDate' }}</td>
                  <td><span class="badge" [class]="'badge-' + agg.trip_type">{{ agg.trip_type }}</span></td>
                  <td>{{ agg.total_trips | number }}</td>
                  <td>{{ agg.total_revenue | currency }}</td>
                  <td>{{ agg.avg_trip_distance | number:'1.2-2' }} mi</td>
                  <td>{{ agg.avg_trip_duration | number:'1.0-0' }} min</td>
                </tr>
              </tbody>
            </table>
            <ng-template #noData>
              <div class="no-data">
                <p>{{ loading ? 'Loading data...' : 'No data available for selected filters' }}</p>
              </div>
            </ng-template>
          </div>
        </section>

        <!-- Recent Trips Table -->
        <section class="data-table">
          <h2>🚖 Recent Trips</h2>
          <div class="pagination-controls">
            <button (click)="prevPage()" [disabled]="currentPage === 1" class="btn-secondary">Previous</button>
            <span>Page {{ currentPage }} of {{ totalPages }}</span>
            <button (click)="nextPage()" [disabled]="currentPage === totalPages" class="btn-secondary">Next</button>
          </div>
          <div class="table-container">
            <table *ngIf="trips.length > 0">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Pickup Time</th>
                  <th>Pickup Location</th>
                  <th>Dropoff Location</th>
                  <th>Distance</th>
                  <th>Amount</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let trip of trips">
                  <td><span class="badge" [class]="'badge-' + trip.trip_type">{{ trip.trip_type }}</span></td>
                  <td>{{ trip.pickup_datetime | date:'short' }}</td>
                  <td>{{ trip.pickup_zone || 'N/A' }}</td>
                  <td>{{ trip.dropoff_zone || 'N/A' }}</td>
                  <td>{{ trip.trip_distance | number:'1.2-2' }}</td>
                  <td>{{ trip.total_amount | currency }}</td>
                  <td>{{ trip.duration_minutes | number:'1.0-0' }} min</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </main>
    </div>
  `,
  styles: [`
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    .container {
      min-height: 100vh;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      padding: 20px;
    }

    header {
      background: white;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      margin-bottom: 20px;
      text-align: center;
    }

    h1 {
      color: #2d3748;
      margin-bottom: 10px;
      font-size: 2.5em;
    }

    h2 {
      color: #2d3748;
      margin-bottom: 20px;
      font-size: 1.5em;
    }

    main {
      max-width: 1400px;
      margin: 0 auto;
    }

    section {
      background: white;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
      margin-bottom: 20px;
    }

    /* Auth Section */
    .auth-section {
      display: none;
    }

    /* Buttons */
    .btn-primary, .btn-secondary {
      padding: 10px 20px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
      transition: all 0.3s;
    }

    .btn-primary {
      background: #667eea;
      color: white;
    }

    .btn-primary:hover {
      background: #5a67d8;
    }

    .btn-secondary {
      background: #e2e8f0;
      color: #2d3748;
    }

    .btn-secondary:hover {
      background: #cbd5e0;
    }

    .btn-secondary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    /* Filters */
    .filters {
      background: #f7fafc;
    }

    .filter-group {
      display: flex;
      gap: 20px;
      flex-wrap: wrap;
      align-items: flex-end;
    }

    .filter-item {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .filter-item label {
      font-weight: 600;
      color: #4a5568;
      font-size: 14px;
    }

    .filter-item input,
    .filter-item select {
      padding: 8px 12px;
      border: 2px solid #e2e8f0;
      border-radius: 6px;
      font-size: 14px;
    }

    /* Charts */
    .chart-container {
      position: relative;
      height: 400px;
    }

    /* Stats Grid */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 20px;
      padding: 20px;
      background: #f7fafc;
    }

    .stat-card {
      background: white;
      padding: 25px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.05);
      text-align: center;
      border-left: 4px solid #667eea;
    }

    .stat-card h3 {
      color: #718096;
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 10px;
      text-transform: uppercase;
    }

    .stat-value {
      font-size: 2em;
      font-weight: bold;
      color: #2d3748;
    }

    /* Tables */
    .table-container {
      overflow-x: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
    }

    thead {
      background: #f7fafc;
    }

    th {
      padding: 12px;
      text-align: left;
      font-weight: 600;
      color: #4a5568;
      border-bottom: 2px solid #e2e8f0;
    }

    td {
      padding: 12px;
      border-bottom: 1px solid #f7fafc;
    }

    tbody tr:hover {
      background: #f7fafc;
    }

    .badge {
      display: inline-block;
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
    }

    .badge-yellow {
      background: #ffd700;
      color: #744210;
    }

    .badge-green {
      background: #48bb78;
      color: white;
    }

    .badge-fhv {
      background: #4299e1;
      color: white;
    }

    .badge-fhvhv {
      background: #9f7aea;
      color: white;
    }

    .no-data {
      text-align: center;
      padding: 40px;
      color: #718096;
    }

    .pagination-controls {
      display: flex;
      gap: 15px;
      align-items: center;
      justify-content: center;
      margin-bottom: 20px;
    }

    small {
      display: block;
      color: #718096;
      margin-top: 5px;
    }

    @media (max-width: 768px) {
      .filter-group {
        flex-direction: column;
      }

      .filter-item {
        width: 100%;
      }

      h1 {
        font-size: 1.8em;
      }
    }
  `]
})
export class AppComponent implements OnInit {
  apiUrl = environment.apiUrl;
  isAuthenticated = false;
  username = '';
  password = '';
  token = '';
  loading = false;

  // Filter state
  startDate = '';
  endDate = '';
  selectedTripType = '';

  // Data
  aggregates: DailyAggregate[] = [];
  trips: Trip[] = [];
  
  // Stats
  totalTrips = 0;
  totalRevenue = 0;
  avgDistance = 0;
  avgDuration = 0;

  // Pagination
  currentPage = 1;
  pageSize = 20;
  revenueChart: Chart | null = null;

  constructor(private http: HttpClient) {
    // Set default date range (last 30 days)
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    this.endDate = today.toISOString().split('T')[0];
    this.startDate = thirtyDaysAgo.toISOString().split('T')[0];
  }

  ngOnInit() {
    this.loadAggregates();
    this.loadTrips();
  }

  login() {
    this.http.post<{access_token: string}>(`${this.apiUrl}/api/auth/login`, {
      username: this.username,
      password: this.password
    }).subscribe({
      next: (response) => {
        this.token = response.access_token;
        this.isAuthenticated = true;
        this.password = '';
        this.loadAggregates();
        this.loadTrips();
      },
      error: (error) => {
        alert('Login failed: ' + (error.error?.detail || 'Invalid credentials'));
      }
    });
  }

  logout() {
    this.isAuthenticated = false;
    this.token = '';
    this.username = '';
  }

  loadAggregates() {
    this.loading = true;
    let url = `${this.apiUrl}/api/aggregates/daily?limit=100`;
    
    
    this.http.get<{total: number, page: number, page_size: number, total_pages: number, data: Trip[]}>(url).subscribe({
      next: (response) => {
        this.trips = response.data;
        this.totalPages = response.total_pages;
      },
      error: (error) => {
        console.error('Error loading trips:', error);
      }
    });
  }

  calculateStats() {
    if (this.aggregates.length === 0) {
      this.totalTrips = 0;
      this.totalRevenue = 0;
      this.avgDistance = 0;
      this.avgDuration = 0;
      return;
    }

    this.totalTrips = this.aggregates.reduce((sum, agg) => sum + agg.total_trips, 0);
    this.totalRevenue = this.aggregates.reduce((sum, agg) => sum + (agg.total_revenue || 0), 0);
    
    const validDistances = this.aggregates.filter(a => a.avg_trip_distance != null);
    this.avgDistance = validDistances.length > 0 
      ? validDistances.reduce((sum, a) => sum + (a.avg_trip_distance || 0), 0) / validDistances.length
      : 0;
    
    const validDurations = this.aggregates.filter(a => a.avg_trip_duration != null);
    this.avgDuration = validDurations.length > 0
      ? validDurations.reduce((sum, a) => sum + (a.avg_trip_duration || 0), 0) / validDurations.length
      : 0;
  }

  updateCharts() {
    // Group data by date for time series
    const dataByDate = new Map<string, {[key: string]: {trips: number, revenue: number}}>();
    
    this.aggregates.forEach(agg => {
      if (!dataByDate.has(agg.trip_date)) {
        dataByDate.set(agg.trip_date, {});
      }
      dataByDate.get(agg.trip_date)![agg.trip_type] = {
        trips: agg.total_trips,
        revenue: agg.total_revenue || 0
      };
    });

    const sortedDates = Array.from(dataByDate.keys()).sort();
    const tripTypes = ['yellow', 'green', 'fhv', 'fhvhv'];
    const colors = {
      yellow: '#ffd700',
      green: '#48bb78',
      fhv: '#4299e1',
      fhvhv: '#9f7aea'
    };

    // Trips Chart
    const tripsDatasets = tripTypes.map(type => ({
      label: type.toUpperCase(),
      data: sortedDates.map(date => dataByDate.get(date)?.[type]?.trips || 0),
      borderColor: colors[type as keyof typeof colors],
      backgroundColor: colors[type as keyof typeof colors] + '40',
      fill: false,
      tension: 0.1
    }));

    // Revenue Chart
    const revenueDatasets = tripTypes.map(type => ({
      label: type.toUpperCase(),
      data: sortedDates.map(date => dataByDate.get(date)?.[type]?.revenue || 0),
      borderColor: colors[type as keyof typeof colors],
      backgroundColor: colors[type as keyof typeof colors] + '40',
      fill: false,
      tension: 0.1
    }));

    // Destroy existing charts
    if (this.tripsChart) this.tripsChart.destroy();
    if (this.revenueChart) this.revenueChart.destroy();

    // Create Trips Chart
    const tripsCtx = document.getElementById('tripsChart') as HTMLCanvasElement;
    if (tripsCtx) {
      this.tripsChart = new Chart(tripsCtx, {
        type: 'line',
        data: {
          labels: sortedDates,
          datasets: tripsDatasets.filter(ds => ds.data.some(d => d > 0))
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            title: {
              display: false
            },
            legend: {
              position: 'top'
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: 'Number of Trips'
              }
            }
          }
        }
      });
    }

    // Create Revenue Chart
    const revenueCtx = document.getElementById('revenueChart') as HTMLCanvasElement;
    if (revenueCtx) {
      this.revenueChart = new Chart(revenueCtx, {
        type: 'line',
        data: {
          labels: sortedDates,
          datasets: revenueDatasets.filter(ds => ds.data.some(d => d > 0))
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            title: {
              display: false
            },
            legend: {
              position: 'top'
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: 'Revenue ($)'
              }
            }
          }
        }
      });
    }
  }

  resetFilters() {
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    this.endDate = today.toISOString().split('T')[0];
    this.startDate = thirtyDaysAgo.toISOString().split('T')[0];
    this.selectedTripType = '';
    this.currentPage = 1;
    
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

    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 20px;
    }

    header {
      text-align: center;
      margin-bottom: 40px;
    }

    h1 {
      color: #0066cc;
      margin-bottom: 10px;
    }

    h2 {
      color: #333;
      margin-bottom: 15px;
    }

    .api-status {
      margin-bottom: 30px;
    }

    .status-card {
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .status-card.connected {
      border-left: 4px solid #28a745;
    }

    .status-card.disconnected {
      border-left: 4px solid #dc3545;
    }

    .status-card p {
      margin: 10px 0;
    }

    .items {
      background: white;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    ul {
      list-style: none;
    }

    li {
      padding: 10px;
      border-bottom: 1px solid #eee;
    }

    li:last-child {
      border-bottom: none;
    }
  `]
})
export class AppComponent implements OnInit {
  apiUrl = environment.apiUrl;
  apiStatus = 'Checking...';
  apiConnected = false;
  items: any[] = [];

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.checkApi();
    this.loadItems();
  }

  checkApi() {
    this.http.get(`${this.apiUrl}/health`).subscribe({
      next: (response: any) => {
        this.apiStatus = response.status || 'Connected';
        this.apiConnected = true;
      },
      error: (error) => {
        this.apiStatus = 'Disconnected - ' + error.message;
        this.apiConnected = false;
      }
    });
  }

  loadItems() {
    this.http.get<any>(`${this.apiUrl}/api/items`).subscribe({
      next: (response) => {
        this.items = response.items || [];
      },
      error: (error) => {
        console.error('Error loading items:', error);
      }
    });
  }
}
