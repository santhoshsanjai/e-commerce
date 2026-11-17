/**
 * Admin menu. Each item names the permission that reveals it; the API enforces the same
 * permission on every endpoint behind the page. Items without a route yet are added in later phases.
 */
import { IconName } from '@shop/shared';

export interface NavItem {
  label: string;
  path: string;
  permission: string;
  icon: IconName;
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', icon: 'grid', path: '/dashboard', permission: 'dashboard.view' },
  { label: 'Orders', icon: 'clipboard', path: '/orders', permission: 'orders.view' },
  { label: 'Dispatch', icon: 'send', path: '/dispatch', permission: 'orders.export' },
  {
    label: 'Courier import',
    icon: 'upload',
    path: '/courier-import',
    permission: 'orders.import_courier',
  },
  { label: 'Products', icon: 'tag', path: '/products', permission: 'products.view' },
  { label: 'Categories', icon: 'folder', path: '/categories', permission: 'categories.view' },
  { label: 'Sales report', icon: 'chart', path: '/reports/sales', permission: 'reports.view' },
  { label: 'Staff', icon: 'users', path: '/staff', permission: 'users.view' },
  { label: 'Roles', icon: 'key', path: '/roles', permission: 'roles.view' },
  { label: 'Storefront', icon: 'palette', path: '/storefront', permission: 'settings.manage' },
  { label: 'Delivery and GST', icon: 'truck', path: '/charges', permission: 'settings.manage' },
  { label: 'Audit log', icon: 'file', path: '/audit-log', permission: 'audit_logs.view' },
];
