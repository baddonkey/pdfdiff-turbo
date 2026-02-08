import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

export interface AppConfig {
  allow_registration: boolean;
  enable_dropzone: boolean;
  file_retention_hours: number;
  job_retention_days: number;
  recaptcha_site_key?: string | null;
}

@Injectable({ providedIn: 'root' })
export class AppConfigService {
  private baseUrl = '/api';

  constructor(private http: HttpClient) {}

  getConfig() {
    return this.http.get<AppConfig>(`${this.baseUrl}/config`);
  }
}
