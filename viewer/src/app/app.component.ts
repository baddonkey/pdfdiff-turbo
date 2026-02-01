import { Component, ElementRef, HostListener, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth.service';
import { TopbarActionsService } from './core/topbar-actions.service';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterOutlet, RouterLink],
  template: `
    <div class="app-shell">
      <header class="topbar">
        <div style="display:flex; align-items:center; gap: 12px;">
          <img src="assets/logo.png" alt="Logo" style="height: 120px; width: 120px; object-fit: contain;" />
          <strong>
            PDFDiff Turbo<ng-container *ngIf="topbar.jobTitle$ | async as jobTitle"> Compare - {{ jobTitle }}</ng-container>
          </strong>
          <ng-container *ngIf="topbar.actions$ | async as actions">
            <ng-container *ngTemplateOutlet="actions"></ng-container>
          </ng-container>
        </div>
        <div style="display:flex; align-items:center; gap: 12px;">
          <div class="menu" #menuRoot>
            <button class="hamburger" type="button" (click)="toggleMenu()" aria-label="Menu">
              <span></span>
              <span></span>
              <span></span>
            </button>
            <div class="menu-panel" *ngIf="menuOpen">
              <div class="menu-section">
                <a *ngIf="!(auth.isAuthenticated())" routerLink="/auth" class="menu-item" (click)="closeMenu()">Sign in</a>
                <div *ngIf="auth.isAuthenticated()" class="menu-user">
                  Signed in <strong>{{ auth.getUserEmail() }}</strong>
                </div>
                <button *ngIf="auth.isAuthenticated()" class="menu-item" (click)="openProfile()">Profile</button>
                <button *ngIf="auth.isAuthenticated()" class="menu-item" (click)="handleLogout()">Logout</button>
                <button class="menu-item" (click)="toggleAbout()">About</button>
              </div>
              <div *ngIf="aboutOpen" class="menu-about">
                <div class="menu-title">PDFDiff Turbo</div>
                <div class="menu-meta">Version {{ version }}</div>
              </div>
            </div>
          </div>
        </div>
      </header>
      <main class="container">
        <router-outlet></router-outlet>
      </main>
    </div>
    <div class="overlay-backdrop" *ngIf="profileOpen">
      <div class="panel">
        <div class="panel-header">
          <h2>Profile</h2>
          <button class="icon-btn" type="button" (click)="closeProfile()">✕</button>
        </div>
        <div class="panel-content">
          <ng-container *ngIf="auth.currentUser$ | async as user; else profileLoading">
            <div class="profile-grid">
              <div class="profile-item">
                <span>Email</span>
                <strong>{{ user.email }}</strong>
              </div>
              <div class="profile-item">
                <span>Role</span>
                <strong>{{ user.role }}</strong>
              </div>
              <div class="profile-item">
                <span>Status</span>
                <strong>{{ user.is_active ? 'Active' : 'Inactive' }}</strong>
              </div>
              <div class="profile-item">
                <span>Created</span>
                <strong>{{ user.created_at | date: 'medium' }}</strong>
              </div>
            </div>
          </ng-container>
          <ng-template #profileLoading>
            <div class="profile-loading">Loading profile…</div>
          </ng-template>

          <div class="profile-divider"></div>

          <h3>Change password</h3>
          <form class="profile-form" (ngSubmit)="submitPasswordChange()">
            <label>Current password</label>
            <input class="input" [(ngModel)]="currentPassword" name="currentPassword" type="password" required />
            <label>New password</label>
            <input class="input" [(ngModel)]="newPassword" name="newPassword" type="password" required />
            <label>Confirm new password</label>
            <input class="input" [(ngModel)]="confirmNewPassword" name="confirmNewPassword" type="password" required />
            <div class="form-row">
              <button class="btn" type="submit" [disabled]="changingPassword">Update password</button>
              <button class="btn secondary" type="button" (click)="resetPasswordForm()" [disabled]="changingPassword">Clear</button>
            </div>
            <p *ngIf="passwordMessage" class="form-success">{{ passwordMessage }}</p>
            <p *ngIf="passwordError" class="form-error">{{ passwordError }}</p>
          </form>
        </div>
      </div>
    </div>
  `
})
export class AppComponent implements OnInit {
  version = environment.version;
  menuOpen = false;
  aboutOpen = false;
  profileOpen = false;
  currentPassword = '';
  newPassword = '';
  confirmNewPassword = '';
  passwordMessage = '';
  passwordError = '';
  changingPassword = false;

  @ViewChild('menuRoot') menuRoot?: ElementRef<HTMLElement>;

  constructor(public auth: AuthService, public topbar: TopbarActionsService) {}

  ngOnInit() {
    if (this.auth.isAuthenticated()) {
      this.auth.fetchMe().subscribe();
    }
  }

  toggleMenu() {
    this.menuOpen = !this.menuOpen;
    if (!this.menuOpen) {
      this.aboutOpen = false;
    }
  }

  closeMenu() {
    this.menuOpen = false;
    this.aboutOpen = false;
  }

  toggleAbout() {
    this.aboutOpen = !this.aboutOpen;
  }

  openProfile() {
    this.closeMenu();
    this.profileOpen = true;
    this.passwordMessage = '';
    this.passwordError = '';
    this.auth.fetchMe().subscribe();
  }

  closeProfile() {
    this.profileOpen = false;
  }

  resetPasswordForm() {
    this.currentPassword = '';
    this.newPassword = '';
    this.confirmNewPassword = '';
  }

  submitPasswordChange() {
    this.passwordMessage = '';
    this.passwordError = '';

    if (this.newPassword !== this.confirmNewPassword) {
      this.passwordError = 'New passwords do not match.';
      return;
    }

    this.changingPassword = true;
    this.auth.changePassword(this.currentPassword, this.newPassword).subscribe({
      next: () => {
        this.passwordMessage = 'Password updated.';
        this.resetPasswordForm();
      },
      error: err => {
        this.passwordError = err?.error?.detail ?? 'Unable to update password.';
        this.changingPassword = false;
      },
      complete: () => {
        this.changingPassword = false;
      }
    });
  }

  handleLogout() {
    this.auth.logout();
    this.closeMenu();
    this.profileOpen = false;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    if (!this.menuOpen || !this.menuRoot) {
      return;
    }
    const target = event.target as Node | null;
    if (target && this.menuRoot.nativeElement.contains(target)) {
      return;
    }
    this.closeMenu();
  }
}
