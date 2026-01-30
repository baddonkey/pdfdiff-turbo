import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AdminService, AdminJob, AdminUser } from '../../core/admin.service';

@Component({
  selector: 'app-admin-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="grid" style="grid-template-columns: 1fr; gap: 16px;">
      <div class="card">
        <h2>Jobs</h2>
        <button class="btn secondary" (click)="loadJobs()">Refresh</button>
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
                <button class="btn" (click)="cancel(job.id)">Cancel</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="card">
        <h2>Users</h2>
        <button class="btn secondary" (click)="loadUsers()">Refresh</button>
        <table class="table" *ngIf="users.length">
          <thead>
            <tr>
              <th>Email</th>
              <th>Role</th>
              <th>Active</th>
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
              <td>
                <button class="btn" (click)="saveUser(user)">Save</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `
})
export class AdminDashboardComponent {
  jobs: AdminJob[] = [];
  users: AdminUser[] = [];

  constructor(private admin: AdminService) {
    this.loadJobs();
    this.loadUsers();
  }

  loadJobs() {
    this.admin.listJobs().subscribe(jobs => (this.jobs = jobs));
  }

  cancel(jobId: string) {
    this.admin.cancelJob(jobId).subscribe(() => this.loadJobs());
  }

  loadUsers() {
    this.admin.listUsers().subscribe(users => (this.users = users));
  }

  saveUser(user: AdminUser) {
    this.admin.updateUser(user.id, { role: user.role, is_active: user.is_active }).subscribe();
  }

  badgeClass(status: string) {
    if (status === 'completed') return 'badge success';
    if (status === 'failed' || status === 'cancelled') return 'badge danger';
    if (status === 'running') return 'badge warn';
    return 'badge neutral';
  }
}
