"""Permission catalogue and default role grants (ADR-0007).

Keys are seeded by migration and are the contract between the API and the admin UI.
Role-to-permission grants are editable at runtime by a Super Admin; these are the defaults only.
"""

PERMISSIONS: dict[str, str] = {
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

SUPER_ADMIN = "Super Admin"
ADMIN = "Admin"
MANAGER = "Manager"

DEFAULT_ROLE_GRANTS: dict[str, list[str]] = {
    SUPER_ADMIN: list(PERMISSIONS),
    ADMIN: [
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
    MANAGER: [
        "dashboard.view",
        "products.view",
        "categories.view",
        "orders.view",
        "orders.export",
        "orders.import_courier",
        "orders.status.update",
    ],
}
