import { Routes } from '@angular/router';
import { authGuard, permissionGuard } from '@shop/shared';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login').then((m) => m.Login),
    title: 'Sign in · Admin',
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layout/shell').then((m) => m.Shell),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        canActivate: [permissionGuard('dashboard.view')],
        loadComponent: () => import('./features/dashboard/dashboard').then((m) => m.Dashboard),
        title: 'Dashboard · Admin',
      },
      {
        path: 'forbidden',
        loadComponent: () => import('./features/forbidden').then((m) => m.Forbidden),
        title: 'No access · Admin',
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
