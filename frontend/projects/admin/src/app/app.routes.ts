import { Routes } from '@angular/router';
import { authGuard, permissionGuard } from '@shop/shared';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login').then((m) => m.Login),
    title: 'Sign in · Admin',
  },
  {
    path: 'forgot-password',
    loadComponent: () => import('@shop/shared').then((m) => m.ForgotPassword),
    title: 'Reset your password · Admin',
  },
  {
    path: 'reset-password',
    loadComponent: () => import('@shop/shared').then((m) => m.ResetPassword),
    // Staff passwords need 12 characters (the API enforces it too).
    data: { minPassword: 12 },
    title: 'Choose a new password · Admin',
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
        path: 'reports/sales',
        canActivate: [permissionGuard('reports.view')],
        loadComponent: () => import('./features/reports/sales-report').then((m) => m.SalesReport),
        title: 'Sales report · Admin',
      },
      {
        path: 'staff',
        canActivate: [permissionGuard('users.view')],
        loadComponent: () => import('./features/staff/staff-list').then((m) => m.StaffList),
        title: 'Staff · Admin',
      },
      {
        path: 'staff/new',
        canActivate: [permissionGuard('users.manage')],
        loadComponent: () => import('./features/staff/staff-form').then((m) => m.StaffForm),
        title: 'Add staff member · Admin',
      },
      {
        path: 'staff/:id',
        canActivate: [permissionGuard('users.view')],
        loadComponent: () => import('./features/staff/staff-form').then((m) => m.StaffForm),
        title: 'Staff member · Admin',
      },
      {
        path: 'roles',
        canActivate: [permissionGuard('roles.view')],
        loadComponent: () => import('./features/roles/role-list').then((m) => m.RoleList),
        title: 'Roles · Admin',
      },
      {
        path: 'roles/new',
        canActivate: [permissionGuard('roles.manage')],
        loadComponent: () => import('./features/roles/role-form').then((m) => m.RoleForm),
        title: 'New role · Admin',
      },
      {
        path: 'roles/:id',
        canActivate: [permissionGuard('roles.view')],
        loadComponent: () => import('./features/roles/role-form').then((m) => m.RoleForm),
        title: 'Role · Admin',
      },
      {
        path: 'storefront',
        canActivate: [permissionGuard('settings.manage')],
        loadComponent: () =>
          import('./features/storefront/storefront-page').then((m) => m.StorefrontPage),
        title: 'Storefront · Admin',
      },
      {
        path: 'audit-log',
        canActivate: [permissionGuard('audit_logs.view')],
        loadComponent: () => import('./features/audit/audit-log').then((m) => m.AuditLog),
        title: 'Audit log · Admin',
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
