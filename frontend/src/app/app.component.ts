import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, HttpClientModule],
  template: `
    <div class="container">
      <header>
        <h1>NYC Application</h1>
        <p>FastAPI + Angular + PostgreSQL</p>
      </header>
      
      <main>
        <section class="api-status">
          <h2>API Status</h2>
          <div class="status-card" [class.connected]="apiConnected" [class.disconnected]="!apiConnected">
            <p><strong>Status:</strong> {{ apiStatus }}</p>
            <p><strong>API URL:</strong> {{ apiUrl }}</p>
          </div>
        </section>

        <section class="items">
          <h2>Items</h2>
          <div *ngIf="items.length > 0; else noItems">
            <ul>
              <li *ngFor="let item of items">{{ item }}</li>
            </ul>
          </div>
          <ng-template #noItems>
            <p>No items available</p>
          </ng-template>
        </section>
      </main>
    </div>
  `,
  styles: [`
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
