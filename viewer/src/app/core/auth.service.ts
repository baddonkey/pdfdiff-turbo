import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private baseUrl = '/api';

  constructor(private http: HttpClient, private router: Router) {}

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
  }

  register(email: string, password: string) {
    return this.http.post(`${this.baseUrl}/auth/register`, { email, password });
  }

  login(email: string, password: string) {
    return this.http.post<TokenPair>(`${this.baseUrl}/auth/login`, { email, password });
  }

  saveTokens(tokens: TokenPair) {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
  }

  logout() {
    const refresh_token = localStorage.getItem('refresh_token');
    if (refresh_token) {
      this.http.post(`${this.baseUrl}/auth/logout`, { refresh_token }).subscribe();
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.router.navigate(['/auth']);
  }
}
