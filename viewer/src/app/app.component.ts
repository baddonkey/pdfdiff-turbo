import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth.service';
import { TopbarActionsService } from './core/topbar-actions.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink],
  template: `
    <div class="app-shell">
      <header class="topbar">
        <div style="display:flex; align-items:center; gap: 12px;">
          <img src="assets/logo.png" alt="Logo" style="height: 84px; width: 84px; object-fit: contain;" />
          <strong>PDFDiff Viewer</strong>
          <ng-container *ngIf="topbar.actions$ | async as actions">
            <ng-container *ngTemplateOutlet="actions"></ng-container>
          </ng-container>
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
  constructor(public auth: AuthService, public topbar: TopbarActionsService) {}
}
