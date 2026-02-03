import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

export interface AppConfig {
  allow_registration: boolean;
  enable_dropzone: boolean;
}

@Injectable({ providedIn: 'root' })
export class AppConfigService {
  private baseUrl = '/api';

  constructor(private http: HttpClient) {}

  getConfig() {
    return this.http.get<AppConfig>(`${this.baseUrl}/config`);
  }
}
