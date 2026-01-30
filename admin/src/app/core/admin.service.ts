import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

export interface AdminJob {
  id: string;
  status: string;
  created_at: string;
  user_id: string;
}

export interface AdminUser {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private baseUrl = '/api/admin';

  constructor(private http: HttpClient) {}

  listJobs() {
    return this.http.get<AdminJob[]>(`${this.baseUrl}/jobs`);
  }

  cancelJob(jobId: string) {
    return this.http.post(`${this.baseUrl}/jobs/${jobId}/cancel`, {});
  }

  listUsers() {
    return this.http.get<AdminUser[]>(`${this.baseUrl}/users`);
  }

  updateUser(userId: string, payload: Partial<AdminUser>) {
    return this.http.patch(`${this.baseUrl}/users/${userId}`, payload);
  }
}
