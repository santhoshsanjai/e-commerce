import { groupPermissions } from './permission-groups';

describe('groupPermissions', () => {
  it('groups by area in menu order and keeps unknown areas under Other', () => {
    const groups = groupPermissions([
      { key: 'users.view', description: 'View staff' },
      { key: 'orders.export', description: 'Export' },
      { key: 'orders.view', description: 'View orders' },
      { key: 'shipping.manage', description: 'Shipping' },
    ]);
    expect(groups.map((g) => g.label)).toEqual(['Orders and delivery', 'Staff', 'Other']);
    expect(groups[0].permissions.map((p) => p.key)).toEqual(['orders.view', 'orders.export']);
  });
});
