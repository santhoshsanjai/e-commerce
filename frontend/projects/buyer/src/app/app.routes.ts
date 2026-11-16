import { inject } from '@angular/core';
import { CanMatchFn, Router, Routes } from '@angular/router';
import { authGuard } from '@shop/shared';

const LISTING_PARAMS = ['q', 'category', 'sort', 'page'];

/** Old and shared links such as `/?q=lamp` still open the product listing. */
const hasListingParams: CanMatchFn = () => {
  const params = inject(Router).currentNavigation()?.extractedUrl.queryParams ?? {};
  return LISTING_PARAMS.some((key) => key in params);
};

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    canMatch: [hasListingParams],
    loadComponent: () => import('./features/catalog/catalog-page').then((m) => m.CatalogPage),
    title: 'Shop',
  },
  {
    path: '',
    pathMatch: 'full',
    loadComponent: () => import('./features/home/home-page').then((m) => m.HomePage),
    data: { fullBleed: true },
  },
  {
    path: 'shop',
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
    path: 'forgot-password',
    loadComponent: () => import('@shop/shared').then((m) => m.ForgotPassword),
    title: 'Reset your password',
  },
  {
    path: 'reset-password',
    loadComponent: () => import('@shop/shared').then((m) => m.ResetPassword),
    title: 'Choose a new password',
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
