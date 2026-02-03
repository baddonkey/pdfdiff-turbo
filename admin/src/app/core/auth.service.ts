import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export interface UserProfile {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private baseUrl = '/api';
  private userEmailKey = 'user_email';
  private userSubject = new BehaviorSubject<UserProfile | null>(null);
  currentUser$ = this.userSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {}

  isAuthenticated(): boolean {
    return !!localStorage.getItem('access_token');
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
    return this.http.get<UserProfile>(`${this.baseUrl}/auth/me`).pipe(
      tap(res => {
        if (res?.email) {
          this.setUserEmail(res.email);
        }
        this.userSubject.next(res ?? null);
      })
    );
  }

  changePassword(currentPassword: string, newPassword: string) {
    return this.http.post(`${this.baseUrl}/auth/change-password`, {
      current_password: currentPassword,
      new_password: newPassword
    });
  }

  logout() {
    const refresh_token = localStorage.getItem('refresh_token');
    if (refresh_token) {
      this.http.post(`${this.baseUrl}/auth/logout`, { refresh_token }).subscribe();
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem(this.userEmailKey);
    this.userSubject.next(null);
    this.router.navigate(['/auth']);
  }
}
