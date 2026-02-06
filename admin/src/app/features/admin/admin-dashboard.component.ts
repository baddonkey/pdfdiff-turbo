import { AfterViewInit, Component, OnDestroy, TemplateRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService, AdminJob, AdminUser, AppConfig, AdminStats } from '../../core/admin.service';
import { TopbarActionsService } from '../../core/topbar-actions.service';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <ng-template #topbarActions>
      <div style="display:flex; gap: 8px;">
        <button
          class="btn secondary"
          [style.background]="activeTab === 'jobs' ? '#f8fafc' : 'var(--theme-secondary)'"
          [style.color]="activeTab === 'jobs' ? '#0f172a' : 'var(--theme-primary)'"
          [style.border]="activeTab === 'jobs' ? '1px solid #cbd5f5' : '1px solid var(--theme-primary)'"
          (click)="setTab('jobs')"
        >Jobs</button>
        <button
          class="btn secondary"
          [style.background]="activeTab === 'users' ? '#f8fafc' : 'var(--theme-secondary)'"
          [style.color]="activeTab === 'users' ? '#0f172a' : 'var(--theme-primary)'"
          [style.border]="activeTab === 'users' ? '1px solid #cbd5f5' : '1px solid var(--theme-primary)'"
          (click)="setTab('users')"
        >Users</button>
        <button
          class="btn secondary"
          [style.background]="activeTab === 'config' ? '#f8fafc' : 'var(--theme-secondary)'"
          [style.color]="activeTab === 'config' ? '#0f172a' : 'var(--theme-primary)'"
          [style.border]="activeTab === 'config' ? '1px solid #cbd5f5' : '1px solid var(--theme-primary)'"
          (click)="setTab('config')"
        >Configuration</button>
        <button
          class="btn secondary"
          [style.background]="activeTab === 'stats' ? '#f8fafc' : 'var(--theme-secondary)'"
          [style.color]="activeTab === 'stats' ? '#0f172a' : 'var(--theme-primary)'"
          [style.border]="activeTab === 'stats' ? '1px solid #cbd5f5' : '1px solid var(--theme-primary)'"
          (click)="setTab('stats')"
        >Statistics</button>
      </div>
    </ng-template>
    <div class="grid" style="grid-template-columns: 1fr; gap: 16px;">
      <div class="card" *ngIf="activeTab === 'jobs'">
        <div style="display:flex; justify-content: space-between; align-items:center; gap: 8px;">
          <h2 style="margin: 0;">Jobs</h2>
          <button class="btn secondary" (click)="loadJobs()">Refresh</button>
        </div>
        <table class="table" *ngIf="jobs.length">
          <thead>
            <tr>
              <th>ID</th>
              <th>User</th>
              <th>Status</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let job of jobs">
              <td>{{ job.id }}</td>
              <td>{{ job.user_id }}</td>
              <td>
                <span class="badge" [ngClass]="badgeClass(job.status)">{{ job.status }}</span>
              </td>
              <td>{{ job.created_at | date: 'short' }}</td>
              <td>
                <button class="btn" *ngIf="canCancel(job.status)" (click)="cancel(job.id)">Cancel</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card" *ngIf="activeTab === 'users'">
        <div style="display:flex; justify-content: space-between; align-items:center; gap: 8px;">
          <h2 style="margin: 0;">Users</h2>
          <button class="btn secondary" (click)="loadUsers()">Refresh</button>
        </div>
        <table class="table" *ngIf="users.length">
          <thead>
            <tr>
              <th>Email</th>
              <th>Role</th>
              <th>Active</th>
              <th>Max files/set</th>
              <th>Max upload (MB)</th>
              <th>Max pages/job</th>
              <th>Max jobs/day</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let user of users">
              <td>{{ user.email }}</td>
              <td>
                <select class="input" [(ngModel)]="user.role">
                  <option value="user">user</option>
                  <option value="admin">admin</option>
                </select>
              </td>
              <td>
                <select class="input" [(ngModel)]="user.is_active">
                  <option [ngValue]="true">active</option>
                  <option [ngValue]="false">inactive</option>
                </select>
              </td>
              <td><input class="input" type="number" min="1" [(ngModel)]="user.max_files_per_set" /></td>
              <td><input class="input" type="number" min="1" [(ngModel)]="user.max_upload_mb" /></td>
              <td><input class="input" type="number" min="1" [(ngModel)]="user.max_pages_per_job" /></td>
              <td><input class="input" type="number" min="1" [(ngModel)]="user.max_jobs_per_user_per_day" /></td>
              <td>
                <button class="btn" (click)="saveUser(user)">Save</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card" *ngIf="activeTab === 'config'">
        <div style="display:flex; justify-content: space-between; align-items:center; gap: 8px;">
          <h2 style="margin: 0;">Configuration</h2>
          <button class="btn secondary" (click)="loadConfig()">Refresh</button>
        </div>
        <div *ngIf="!config" style="margin-top: 12px; color:#64748b;">Loading configuration...</div>
        <div *ngIf="config" style="margin-top: 12px; display: grid; gap: 12px; max-width: 520px;">
          <label style="display:flex; align-items:center; gap: 10px;">
            <input type="checkbox" [(ngModel)]="config.allow_registration" />
            <span>Enable registration</span>
          </label>
          <label style="display:flex; align-items:center; gap: 10px;">
            <input type="checkbox" [(ngModel)]="config.enable_dropzone" />
            <span>Enable dropzone</span>
          </label>
          <label style="display:grid; gap: 6px;">
            <span>Keep files for (hours)</span>
            <input class="input" type="number" min="1" [(ngModel)]="config.file_retention_hours" />
          </label>
          <label style="display:grid; gap: 6px;">
            <span>Keep job data for (days)</span>
            <input class="input" type="number" min="1" [(ngModel)]="config.job_retention_days" />
          </label>
          <div style="display:flex; gap: 8px; align-items:center;">
            <button class="btn" (click)="saveConfig()">Save</button>
          </div>
          <div *ngIf="configMessage" style="color:#166534;">{{ configMessage }}</div>
          <div *ngIf="configError" style="color:#b91c1c;">{{ configError }}</div>
        </div>
      </div>

      <div class="card" *ngIf="activeTab === 'stats'">
        <div style="display:flex; justify-content: space-between; align-items:center; gap: 8px;">
          <h2 style="margin: 0;">Statistics</h2>
          <button class="btn secondary" (click)="loadStats()">Refresh</button>
        </div>
        <div *ngIf="statsLoading" style="margin-top: 12px; color:#64748b;">Loading statistics...</div>
        <div *ngIf="statsError" style="margin-top: 12px; color:#b91c1c;">{{ statsError }}</div>

        <div *ngIf="stats" style="margin-top: 12px; display: grid; gap: 16px;">
          <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px;">
            <div class="card" style="margin: 0;">
              <div style="font-size: 12px; color:#64748b;">Total jobs</div>
              <div style="font-size: 20px; font-weight: 600;">{{ stats.counts.jobs_total }}</div>
            </div>
            <div class="card" style="margin: 0;">
              <div style="font-size: 12px; color:#64748b;">Job files</div>
              <div style="font-size: 20px; font-weight: 600;">{{ stats.counts.job_files_total }}</div>
            </div>
            <div class="card" style="margin: 0;">
              <div style="font-size: 12px; color:#64748b;">Pages</div>
              <div style="font-size: 20px; font-weight: 600;">{{ stats.counts.pages_total }}</div>
            </div>
            <div class="card" style="margin: 0;">
              <div style="font-size: 12px; color:#64748b;">PDF files</div>
              <div style="font-size: 20px; font-weight: 600;">{{ stats.counts.pdf_files_total }}</div>
            </div>
            <div class="card" style="margin: 0;">
              <div style="font-size: 12px; color:#64748b;">Overlay images</div>
              <div style="font-size: 20px; font-weight: 600;">{{ stats.counts.overlay_images_total }}</div>
            </div>
          </div>

          <div class="card" style="margin: 0;">
            <h3 style="margin-top: 0;">Jobs by status</h3>
            <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px;">
              <div *ngFor="let item of jobStatusEntries(stats.counts.jobs_by_status)" class="card" style="margin: 0;">
                <div style="font-size: 12px; color:#64748b;">{{ item.key }}</div>
                <div style="font-size: 18px; font-weight: 600;">{{ item.value }}</div>
              </div>
            </div>
          </div>

          <div class="card" style="margin: 0;">
            <h3 style="margin-top: 0;">Storage</h3>
            <div style="display:grid; gap: 6px;">
              <div><strong>Data directory:</strong> {{ stats.storage.data_dir }}</div>
              <div><strong>Total:</strong> {{ formatBytes(stats.storage.total_bytes) }}</div>
              <div><strong>Used:</strong> {{ formatBytes(stats.storage.used_bytes) }}</div>
              <div><strong>Free:</strong> {{ formatBytes(stats.storage.free_bytes) }}</div>
            </div>
            <table class="table" style="margin-top: 12px;">
              <thead>
                <tr>
                  <th>Bucket</th>
                  <th>Path</th>
                  <th>Size</th>
                  <th>Files</th>
                  <th>PDFs</th>
                  <th>Images</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let bucket of stats.storage.buckets">
                  <td>{{ bucket.name }}</td>
                  <td>{{ bucket.path }}</td>
                  <td>{{ formatBytes(bucket.bytes) }}</td>
                  <td>{{ bucket.files }}</td>
                  <td>{{ bucket.pdf_files }}</td>
                  <td>{{ bucket.image_files }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="card" style="margin: 0;">
            <h3 style="margin-top: 0;">System</h3>
            <div class="grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px;">
              <div class="card" style="margin: 0;">
                <div style="font-size: 12px; color:#64748b;">CPU count</div>
                <div style="font-size: 18px; font-weight: 600;">{{ formatNullable(stats.system.cpu_count) }}</div>
              </div>
              <div class="card" style="margin: 0;">
                <div style="font-size: 12px; color:#64748b;">Load avg (1/5/15m)</div>
                <div style="font-size: 18px; font-weight: 600;">
                  {{ formatLoad(stats.system.load_avg_1m, stats.system.load_avg_5m, stats.system.load_avg_15m) }}
                </div>
              </div>
              <div class="card" style="margin: 0;">
                <div style="font-size: 12px; color:#64748b;">Memory used</div>
                <div style="font-size: 18px; font-weight: 600;">
                  {{ formatBytes(stats.system.memory_used_bytes) }}
                  <span *ngIf="stats.system.memory_used_percent !== null" style="font-size: 12px; color:#64748b;">
                    ({{ stats.system.memory_used_percent | number: '1.0-1' }}%)
                  </span>
                </div>
              </div>
              <div class="card" style="margin: 0;">
                <div style="font-size: 12px; color:#64748b;">Memory available</div>
                <div style="font-size: 18px; font-weight: 600;">{{ formatBytes(stats.system.memory_available_bytes) }}</div>
              </div>
              <div class="card" style="margin: 0;">
                <div style="font-size: 12px; color:#64748b;">Memory total</div>
                <div style="font-size: 18px; font-weight: 600;">{{ formatBytes(stats.system.memory_total_bytes) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
})
export class AdminDashboardComponent implements AfterViewInit, OnDestroy {
  jobs: AdminJob[] = [];
  users: AdminUser[] = [];
  activeTab: 'jobs' | 'users' | 'config' | 'stats' = 'jobs';
  config: AppConfig | null = null;
  configMessage = '';
  configError = '';
  stats: AdminStats | null = null;
  statsLoading = false;
  statsError = '';

  @ViewChild('topbarActions') topbarActionsTpl?: TemplateRef<any>;

  constructor(private admin: AdminService, private topbar: TopbarActionsService) {
    this.loadJobs();
    this.loadUsers();
    this.loadConfig();
    this.loadStats();
  }

  ngAfterViewInit() {
    setTimeout(() => this.topbar.setActions(this.topbarActionsTpl ?? null), 0);
  }

  ngOnDestroy() {
    this.topbar.setActions(null);
  }

  setTab(tab: 'jobs' | 'users' | 'config' | 'stats') {
    this.activeTab = tab;
    if (tab === 'config' && !this.config) {
      this.loadConfig();
    }
    if (tab === 'stats' && !this.stats) {
      this.loadStats();
    }
  }

  loadJobs() {
    this.admin.listJobs().subscribe(jobs => (this.jobs = jobs));
  }

  cancel(jobId: string) {
    this.admin.cancelJob(jobId).subscribe(() => this.loadJobs());
  }

  canCancel(status: string) {
    return status !== 'completed' && status !== 'failed' && status !== 'cancelled';
  }

  loadUsers() {
    this.admin.listUsers().subscribe(users => (this.users = users));
  }

  saveUser(user: AdminUser) {
    this.admin.updateUser(user.id, {
      role: user.role,
      is_active: user.is_active,
      max_files_per_set: user.max_files_per_set,
      max_upload_mb: user.max_upload_mb,
      max_pages_per_job: user.max_pages_per_job,
      max_jobs_per_user_per_day: user.max_jobs_per_user_per_day
    }).subscribe();
  }

  loadConfig() {
    this.configMessage = '';
    this.configError = '';
    this.admin.getConfig().subscribe({
      next: config => {
        this.config = { ...config };
      },
      error: err => {
        this.configError = err?.error?.detail ?? 'Failed to load configuration.';
      }
    });
  }

  saveConfig() {
    if (!this.config) {
      return;
    }
    this.configMessage = '';
    this.configError = '';
    this.admin.updateConfig({
      allow_registration: this.config.allow_registration,
      enable_dropzone: this.config.enable_dropzone,
      file_retention_hours: this.config.file_retention_hours,
      job_retention_days: this.config.job_retention_days
    }).subscribe({
      next: config => {
        this.config = { ...config };
        this.configMessage = 'Configuration saved.';
      },
      error: err => {
        this.configError = err?.error?.detail ?? 'Failed to save configuration.';
      }
    });
  }

  loadStats() {
    this.statsLoading = true;
    this.statsError = '';
    this.admin.getStats().subscribe({
      next: stats => {
        this.stats = stats;
      },
      error: err => {
        this.statsError = err?.error?.detail ?? 'Failed to load statistics.';
      },
      complete: () => {
        this.statsLoading = false;
      }
    });
  }

  formatBytes(value: number | null) {
    if (value === null || value === undefined) {
      return 'n/a';
    }
    if (value === 0) {
      return '0 B';
    }
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const index = Math.min(units.length - 1, Math.floor(Math.log(value) / Math.log(1024)));
    const scaled = value / Math.pow(1024, index);
    return `${scaled.toFixed(scaled < 10 ? 2 : 1)} ${units[index]}`;
  }

  formatNullable(value: number | null) {
    return value === null || value === undefined ? 'n/a' : value;
  }

  formatLoad(avg1: number | null, avg5: number | null, avg15: number | null) {
    if (avg1 === null || avg5 === null || avg15 === null) {
      return 'n/a';
    }
    return `${avg1.toFixed(2)} / ${avg5.toFixed(2)} / ${avg15.toFixed(2)}`;
  }

  jobStatusEntries(statuses: Record<string, number>) {
    return Object.entries(statuses).map(([key, value]) => ({ key, value }));
  }

  badgeClass(status: string) {
    if (status === 'completed') return 'badge success';
    if (status === 'failed' || status === 'cancelled') return 'badge danger';
    if (status === 'running') return 'badge warn';
    return 'badge neutral';
  }
}
