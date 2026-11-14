"""seed permissions and system roles

Data is written out literally so this migration never changes when app code does.
Later permission changes get their own migration.

Revision ID: 0002
Revises: 0001
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = {
    "dashboard.view": "View the admin dashboard",
    "products.view": "View products",
    "products.create": "Create products",
    "products.update": "Edit products",
    "products.publish": "Publish and unpublish products",
    "products.archive": "Archive products",
    "categories.view": "View categories",
    "categories.manage": "Create, edit and reorder categories",
    "orders.view": "View orders",
    "orders.export": "Create dispatch batches and download courier exports",
    "orders.import_courier": "Upload and confirm courier status files",
    "orders.status.update": "Manually update an order's status",
    "orders.status.override": "Override order status transition rules",
    "users.view": "View staff and buyer accounts",
    "users.manage": "Create, edit and deactivate staff accounts",
    "roles.view": "View roles and permissions",
    "roles.manage": "Create and edit roles and their permissions",
    "reports.view": "View reports",
    "audit_logs.view": "View the audit log",
}

ROLES = {
    "Super Admin": "Full system access, including staff, roles and configuration",
    "Admin": "Operational access to products and orders as granted",
    "Manager": "Limited operational access, e.g. orders and courier files",
}

GRANTS = {
    "Super Admin": [
        "dashboard.view",
        "products.view",
        "products.create",
        "products.update",
        "products.publish",
        "products.archive",
        "categories.view",
        "categories.manage",
        "orders.view",
        "orders.export",
        "orders.import_courier",
        "orders.status.update",
        "orders.status.override",
        "users.view",
        "users.manage",
        "roles.view",
        "roles.manage",
        "reports.view",
        "audit_logs.view",
    ],
    "Admin": [
        "dashboard.view",
        "products.view",
        "products.create",
        "products.update",
        "products.publish",
        "products.archive",
        "categories.view",
        "categories.manage",
        "orders.view",
        "orders.export",
        "orders.import_courier",
        "orders.status.update",
        "users.view",
        "roles.view",
        "reports.view",
        "audit_logs.view",
    ],
    "Manager": [
        "dashboard.view",
        "products.view",
        "categories.view",
        "orders.view",
        "orders.export",
        "orders.import_courier",
        "orders.status.update",
    ],
}

permissions_t = sa.table(
    "permissions",
    sa.column("id", sa.Uuid),
    sa.column("key", sa.String),
    sa.column("description", sa.String),
)
roles_t = sa.table(
    "roles",
    sa.column("id", sa.Uuid),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    sa.column("is_system", sa.Boolean),
)
role_permissions_t = sa.table(
    "role_permissions", sa.column("role_id", sa.Uuid), sa.column("permission_id", sa.Uuid)
)


def upgrade() -> None:
    perm_ids = {key: uuid.uuid4() for key in PERMISSIONS}
    role_ids = {name: uuid.uuid4() for name in ROLES}
    op.bulk_insert(
        permissions_t,
        [{"id": perm_ids[k], "key": k, "description": d} for k, d in PERMISSIONS.items()],
    )
    op.bulk_insert(
        roles_t,
        [
            {"id": role_ids[n], "name": n, "description": d, "is_system": True}
            for n, d in ROLES.items()
        ],
    )
    op.bulk_insert(
        role_permissions_t,
        [
            {"role_id": role_ids[role], "permission_id": perm_ids[key]}
            for role, keys in GRANTS.items()
            for key in keys
        ],
    )


def downgrade() -> None:
    op.execute(roles_t.delete().where(roles_t.c.name.in_(list(ROLES))))
    op.execute(permissions_t.delete().where(permissions_t.c.key.in_(list(PERMISSIONS))))
