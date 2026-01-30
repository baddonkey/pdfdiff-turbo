import { Routes } from '@angular/router';
import { AuthComponent } from './features/auth/auth.component';
import { AdminDashboardComponent } from './features/admin/admin-dashboard.component';
import { authGuard } from './core/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'admin', pathMatch: 'full' },
  { path: 'auth', component: AuthComponent },
  { path: 'admin', component: AdminDashboardComponent, canActivate: [authGuard] }
];
