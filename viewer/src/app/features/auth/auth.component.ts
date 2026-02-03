import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { AppConfigService } from '../../core/app-config.service';

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
          <button class="btn" type="submit" style="margin-top: 10px;">Sign In</button>
        </form>
        <p *ngIf="error" style="color:#b91c1c;">{{ error }}</p>
      </div>
      <div class="card" *ngIf="registrationEnabled; else registrationDisabled">
        <h2>Create Account</h2>
        <form (ngSubmit)="register()">
          <label>Email</label>
          <input class="input" [(ngModel)]="registerEmail" name="registerEmail" type="email" required />
          <label>Password</label>
          <input class="input" [(ngModel)]="registerPassword" name="registerPassword" type="password" required />
          <button class="btn secondary" type="submit" style="margin-top: 10px;">Register</button>
        </form>
        <p *ngIf="message" style="color:#166534;">{{ message }}</p>
      </div>
      <ng-template #registrationDisabled>
        <div class="card">
          <h2>Registration</h2>
          <p style="color:#64748b;">Registration is currently disabled.</p>
        </div>
      </ng-template>
    </div>
  `
})
export class AuthComponent implements OnInit {
  loginEmail = '';
  loginPassword = '';
  registerEmail = '';
  registerPassword = '';
  message = '';
  error = '';
  registrationEnabled = true;

  constructor(private auth: AuthService, private router: Router, private config: AppConfigService) {}

  ngOnInit() {
    this.config.getConfig().subscribe({
      next: cfg => {
        this.registrationEnabled = cfg.allow_registration;
      },
      error: () => {
        this.registrationEnabled = true;
      }
    });
  }

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
