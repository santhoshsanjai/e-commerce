import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/catalog/catalog-page').then((m) => m.CatalogPage),
    title: 'Shop',
  },
  {
    path: 'products/:slug',
    loadComponent: () => import('./features/catalog/product-page').then((m) => m.ProductPage),
    title: 'Product',
  },
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login').then((m) => m.Login),
    title: 'Sign in',
  },
  {
    path: 'register',
    loadComponent: () => import('./features/auth/register').then((m) => m.Register),
    title: 'Create account',
  },
  {
    path: '**',
    loadComponent: () => import('./features/not-found').then((m) => m.NotFound),
    title: 'Page not found',
  },
];
