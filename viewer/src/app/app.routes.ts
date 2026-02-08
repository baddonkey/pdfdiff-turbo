import { Routes } from '@angular/router';
import { AuthComponent } from './features/auth/auth.component';
import { JobsComponent } from './features/jobs/jobs.component';
import { ViewerComponent } from './features/viewer/viewer.component';
import { TextViewerComponent } from './features/text-viewer/text-viewer.component';
import { authGuard } from './core/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'jobs', pathMatch: 'full' },
  { path: 'auth', component: AuthComponent },
  { path: 'jobs', component: JobsComponent, canActivate: [authGuard] },
  { path: 'jobs/:jobId/files/:fileId', component: ViewerComponent, canActivate: [authGuard] },
  { path: 'jobs/:jobId/files/:fileId/text', component: TextViewerComponent, canActivate: [authGuard] }
];
