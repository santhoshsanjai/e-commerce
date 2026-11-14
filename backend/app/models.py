"""Import every model so SQLAlchemy metadata (and Alembic autogenerate) sees all tables."""

from app.modules.access_control.models import Permission, Role
from app.modules.audit.models import AuditLog
from app.modules.auth.models import RefreshToken
from app.modules.catalog.models import (
    Brand,
    Category,
    Product,
    ProductAttribute,
    ProductMedia,
    ProductSku,
)
from app.modules.users.models import User

__all__ = [
    "AuditLog",
    "Brand",
    "Category",
    "Permission",
    "Product",
    "ProductAttribute",
    "ProductMedia",
    "ProductSku",
    "RefreshToken",
    "Role",
    "User",
]
