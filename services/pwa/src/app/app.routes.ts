import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';

/**
 * Routes de l'application (standalone, lazy-loading par fonctionnalité).
 * `/login` est public ; la coquille authentifiée est protégée par `authGuard`.
 */
export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login.component').then((m) => m.LoginComponent),
  },
  {
    path: '',
    loadComponent: () => import('./layout/shell.component').then((m) => m.ShellComponent),
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'parcel/:parcel',
        loadComponent: () =>
          import('./features/parcel-detail/parcel-detail.component').then(
            (m) => m.ParcelDetailComponent,
          ),
      },
      {
        path: 'alerts',
        loadComponent: () =>
          import('./features/alerts/alerts.component').then((m) => m.AlertsComponent),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
