import { AfterViewInit, Component, OnDestroy, TemplateRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService, AdminJob, AdminUser, AppConfig } from '../../core/admin.service';
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
    </div>
  `
})
export class AdminDashboardComponent implements AfterViewInit, OnDestroy {
  jobs: AdminJob[] = [];
  users: AdminUser[] = [];
  activeTab: 'jobs' | 'users' | 'config' = 'jobs';
  config: AppConfig | null = null;
  configMessage = '';
  configError = '';

  @ViewChild('topbarActions') topbarActionsTpl?: TemplateRef<any>;

  constructor(private admin: AdminService, private topbar: TopbarActionsService) {
    this.loadJobs();
    this.loadUsers();
    this.loadConfig();
  }

  ngAfterViewInit() {
    setTimeout(() => this.topbar.setActions(this.topbarActionsTpl ?? null), 0);
  }

  ngOnDestroy() {
    this.topbar.setActions(null);
  }

  setTab(tab: 'jobs' | 'users' | 'config') {
    this.activeTab = tab;
    if (tab === 'config' && !this.config) {
      this.loadConfig();
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

  badgeClass(status: string) {
    if (status === 'completed') return 'badge success';
    if (status === 'failed' || status === 'cancelled') return 'badge danger';
    if (status === 'running') return 'badge warn';
    return 'badge neutral';
  }
}
