import { Routes } from '@angular/router';

/**
 * Routes de l'application (lazy-loading par fonctionnalité).
 * Les écrans métier (login, dashboard, détail, alertes) sont ajoutés en Phase 4 ;
 * le scaffold pointe pour l'instant sur un écran d'accueil placeholder.
 */
export const routes: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./features/home/home.component').then((m) => m.HomeComponent),
  },
  { path: '**', redirectTo: '' },
];
