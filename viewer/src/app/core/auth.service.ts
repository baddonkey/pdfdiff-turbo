import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap } from 'rxjs/operators';

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private baseUrl = '/api';
  private userEmailKey = 'user_email';

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

  setUserEmail(email: string) {
    if (email) {
      localStorage.setItem(this.userEmailKey, email);
    }
  }

  getUserEmail(): string {
    return localStorage.getItem(this.userEmailKey) || '';
  }

  fetchMe() {
    return this.http.get<{ email: string }>(`${this.baseUrl}/auth/me`).pipe(
      tap(res => {
        if (res?.email) {
          this.setUserEmail(res.email);
        }
      })
    );
  }

  logout() {
    const refresh_token = localStorage.getItem('refresh_token');
    if (refresh_token) {
      this.http.post(`${this.baseUrl}/auth/logout`, { refresh_token }).subscribe();
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem(this.userEmailKey);
    this.router.navigate(['/auth']);
  }
}
