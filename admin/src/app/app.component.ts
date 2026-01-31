import { Component, ElementRef, HostListener, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterOutlet } from '@angular/router';
import { AuthService } from './core/auth.service';
import { environment } from '../environments/environment';

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
        <div class="menu" #menuRoot>
          <button class="hamburger" type="button" (click)="toggleMenu()" aria-label="Menu">
            <span></span>
            <span></span>
            <span></span>
          </button>
          <div class="menu-panel" *ngIf="menuOpen">
            <div class="menu-section">
              <a *ngIf="!(auth.isAuthenticated())" routerLink="/auth" class="menu-item" (click)="closeMenu()">Sign in</a>
              <button *ngIf="auth.isAuthenticated()" class="menu-item" (click)="handleLogout()">Logout</button>
              <button class="menu-item" (click)="toggleAbout()">About</button>
            </div>
            <div *ngIf="aboutOpen" class="menu-about">
              <div class="menu-title">PDFDiff Admin</div>
              <div class="menu-meta">Version {{ version }}</div>
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
export class AppComponent {
  version = environment.version;
  menuOpen = false;
  aboutOpen = false;

  @ViewChild('menuRoot') menuRoot?: ElementRef<HTMLElement>;

  constructor(public auth: AuthService) {}

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
