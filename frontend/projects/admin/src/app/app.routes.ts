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
        path: 'orders',
        canActivate: [permissionGuard('orders.view')],
        loadComponent: () => import('./features/orders/order-list').then((m) => m.OrderList),
        title: 'Orders · Admin',
      },
      {
        path: 'orders/:id',
        canActivate: [permissionGuard('orders.view')],
        loadComponent: () => import('./features/orders/order-detail').then((m) => m.OrderDetail),
        title: 'Order · Admin',
      },
      {
        path: 'dispatch',
        canActivate: [permissionGuard('orders.export')],
        loadComponent: () =>
          import('./features/dispatch/dispatch-page').then((m) => m.DispatchPage),
        title: 'Dispatch · Admin',
      },
      {
        path: 'courier-import',
        canActivate: [permissionGuard('orders.import_courier')],
        loadComponent: () =>
          import('./features/courier-import/courier-import-page').then((m) => m.CourierImportPage),
        title: 'Courier import · Admin',
      },
      {
        path: 'products',
        canActivate: [permissionGuard('products.view')],
        loadComponent: () => import('./features/products/product-list').then((m) => m.ProductList),
        title: 'Products · Admin',
      },
      {
        path: 'products/new',
        canActivate: [permissionGuard('products.create')],
        loadComponent: () => import('./features/products/product-form').then((m) => m.ProductForm),
        title: 'New product · Admin',
      },
      {
        path: 'products/:id',
        canActivate: [permissionGuard('products.view')],
        loadComponent: () => import('./features/products/product-form').then((m) => m.ProductForm),
        title: 'Product · Admin',
      },
      {
        path: 'categories',
        canActivate: [permissionGuard('categories.view')],
        loadComponent: () =>
          import('./features/categories/category-list').then((m) => m.CategoryList),
        title: 'Categories · Admin',
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
