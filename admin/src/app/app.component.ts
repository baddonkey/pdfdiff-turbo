import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink],
  template: `
    <div class="app-shell">
      <header class="topbar">
        <div>
          <strong>PDFDiff Admin</strong>
        </div>
        <div>
          <a *ngIf="!(auth.isAuthenticated())" routerLink="/auth">Sign in</a>
          <button *ngIf="auth.isAuthenticated()" class="btn secondary" (click)="auth.logout()">Logout</button>
        </div>
      </header>
      <main class="container">
        <router-outlet></router-outlet>
      </main>
    </div>
  `
})
export class AppComponent {
  constructor(public auth: AuthService) {}
}
