/**
 * Admin menu. Each item names the permission that reveals it; the API enforces the same
 * permission on every endpoint behind the page. Items without a route yet are added in later phases.
 */
export interface NavItem {
  label: string;
  path: string;
  permission: string;
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: '/dashboard', permission: 'dashboard.view' },
];
