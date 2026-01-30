import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-auth',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="grid two">
      <div class="card">
        <h2>Sign In</h2>
        <form (ngSubmit)="login()">
          <label>Email</label>
          <input class="input" [(ngModel)]="loginEmail" name="loginEmail" type="email" required />
          <label>Password</label>
          <input class="input" [(ngModel)]="loginPassword" name="loginPassword" type="password" required />
          <button class="btn" type="submit">Sign In</button>
        </form>
        <p *ngIf="error" style="color:#b91c1c;">{{ error }}</p>
      </div>
      <div class="card">
        <h2>Create Account</h2>
        <form (ngSubmit)="register()">
          <label>Email</label>
          <input class="input" [(ngModel)]="registerEmail" name="registerEmail" type="email" required />
          <label>Password</label>
          <input class="input" [(ngModel)]="registerPassword" name="registerPassword" type="password" required />
          <button class="btn secondary" type="submit">Register</button>
        </form>
        <p *ngIf="message" style="color:#166534;">{{ message }}</p>
      </div>
    </div>
  `
})
export class AuthComponent {
  loginEmail = '';
  loginPassword = '';
  registerEmail = '';
  registerPassword = '';
  message = '';
  error = '';

  constructor(private auth: AuthService, private router: Router) {}

  login() {
    this.message = '';
    this.error = '';
    this.auth.login(this.loginEmail, this.loginPassword).subscribe({
      next: tokens => {
        this.auth.saveTokens(tokens);
        this.auth.setUserEmail(this.loginEmail);
        this.router.navigate(['/jobs']);
      },
      error: err => {
        this.error = err?.error?.detail ?? 'Login failed.';
      }
    });
  }

  register() {
    this.message = '';
    this.error = '';
    this.auth.register(this.registerEmail, this.registerPassword).subscribe({
      next: () => {
        this.loginEmail = this.registerEmail;
        this.loginPassword = this.registerPassword;
        this.message = 'Registered. You can sign in now.';
      },
      error: err => {
        this.error = err?.error?.detail ?? 'Registration failed.';
      }
    });
  }
}
