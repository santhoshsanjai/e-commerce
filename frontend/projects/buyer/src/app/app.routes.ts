import { Routes } from '@angular/router';
import { authGuard } from '@shop/shared';

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
    path: 'cart',
    canActivate: [authGuard],
    loadComponent: () => import('./features/cart/cart-page').then((m) => m.CartPage),
    title: 'Your cart',
  },
  {
    path: 'checkout',
    canActivate: [authGuard],
    loadComponent: () => import('./features/checkout/checkout-page').then((m) => m.CheckoutPage),
    title: 'Checkout',
  },
  {
    path: 'orders',
    canActivate: [authGuard],
    loadComponent: () => import('./features/orders/order-list-page').then((m) => m.OrderListPage),
    title: 'My orders',
  },
  {
    path: 'orders/:orderNumber',
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/orders/order-detail-page').then((m) => m.OrderDetailPage),
    title: 'Order',
  },
  {
    path: 'account',
    canActivate: [authGuard],
    loadComponent: () => import('./features/account/account-page').then((m) => m.AccountPage),
    title: 'Your account',
  },
  {
    path: '**',
    loadComponent: () => import('./features/not-found').then((m) => m.NotFound),
    title: 'Page not found',
  },
];
