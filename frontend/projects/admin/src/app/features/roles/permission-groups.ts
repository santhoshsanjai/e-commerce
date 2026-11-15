import { PermissionInfo } from '../staff/staff.api';

/** Human names for the first part of a permission key, in menu order. */
const AREAS: [prefix: string, label: string][] = [
  ['dashboard', 'Dashboard'],
  ['orders', 'Orders and delivery'],
  ['products', 'Products'],
  ['categories', 'Categories'],
  ['reports', 'Reports'],
  ['users', 'Staff'],
  ['roles', 'Roles'],
  ['audit_logs', 'Audit log'],
];

export interface PermissionGroup {
  label: string;
  permissions: PermissionInfo[];
}

/** Group permissions by area so the role editor reads like the admin menu. */
export function groupPermissions(all: PermissionInfo[]): PermissionGroup[] {
  const groups = new Map<string, PermissionInfo[]>();
  for (const p of all) {
    const prefix = p.key.split('.')[0];
    groups.set(prefix, [...(groups.get(prefix) ?? []), p]);
  }
  // "View" comes first in each area: it is what every other permission there builds on.
  const viewFirst = (perms: PermissionInfo[]) =>
    [...perms].sort((a, b) => Number(!a.key.endsWith('.view')) - Number(!b.key.endsWith('.view')));
  const known = AREAS.filter(([prefix]) => groups.has(prefix)).map(([prefix, label]) => ({
    label,
    permissions: viewFirst(groups.get(prefix) ?? []),
  }));
  const knownPrefixes = new Set(AREAS.map(([prefix]) => prefix));
  const other = [...groups.entries()]
    .filter(([prefix]) => !knownPrefixes.has(prefix))
    .flatMap(([, perms]) => perms);
  return other.length ? [...known, { label: 'Other', permissions: other }] : known;
}
