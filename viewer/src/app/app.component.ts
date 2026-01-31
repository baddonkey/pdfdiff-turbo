import { Component, ElementRef, HostListener, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth.service';
import { TopbarActionsService } from './core/topbar-actions.service';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink],
  template: `
    <div class="app-shell">
      <header class="topbar">
        <div style="display:flex; align-items:center; gap: 12px;">
          <img src="assets/logo.png" alt="Logo" style="height: 120px; width: 120px; object-fit: contain;" />
          <strong>
            PDFDiff Viewer<ng-container *ngIf="topbar.jobTitle$ | async as jobTitle"> Compare - {{ jobTitle }}</ng-container>
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
                <button *ngIf="auth.isAuthenticated()" class="menu-item" (click)="handleLogout()">Logout</button>
                <button class="menu-item" (click)="toggleAbout()">About</button>
              </div>
              <div *ngIf="aboutOpen" class="menu-about">
                <div class="menu-title">PDFDiff Viewer</div>
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
  `
})
export class AppComponent implements OnInit {
  version = environment.version;
  menuOpen = false;
  aboutOpen = false;

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

  handleLogout() {
    this.auth.logout();
    this.closeMenu();
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
