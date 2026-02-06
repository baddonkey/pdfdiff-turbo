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
  max_files_per_set: number;
  max_upload_mb: number;
  max_pages_per_job: number;
  max_jobs_per_user_per_day: number;
  created_at: string;
}

export interface AppConfig {
  allow_registration: boolean;
  enable_dropzone: boolean;
  file_retention_hours: number;
  job_retention_days: number;
}

export interface AdminStorageBucket {
  name: string;
  path: string;
  bytes: number;
  files: number;
  pdf_files: number;
  image_files: number;
}

export interface AdminStorageStats {
  data_dir: string;
  total_bytes: number | null;
  used_bytes: number | null;
  free_bytes: number | null;
  buckets: AdminStorageBucket[];
}

export interface AdminCounts {
  jobs_total: number;
  jobs_by_status: Record<string, number>;
  job_files_total: number;
  pages_total: number;
  pdf_files_total: number;
  overlay_images_total: number;
}

export interface AdminSystemStats {
  cpu_count: number | null;
  load_avg_1m: number | null;
  load_avg_5m: number | null;
  load_avg_15m: number | null;
  memory_total_bytes: number | null;
  memory_used_bytes: number | null;
  memory_available_bytes: number | null;
  memory_used_percent: number | null;
}

export interface AdminStats {
  generated_at: string;
  storage: AdminStorageStats;
  counts: AdminCounts;
  system: AdminSystemStats;
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

  getConfig() {
    return this.http.get<AppConfig>(`${this.baseUrl}/config`);
  }

  updateConfig(payload: Partial<AppConfig>) {
    return this.http.patch<AppConfig>(`${this.baseUrl}/config`, payload);
  }

  getStats() {
    return this.http.get<AdminStats>(`${this.baseUrl}/stats`);
  }
}
