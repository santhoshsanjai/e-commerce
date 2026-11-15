"""Import every model so SQLAlchemy metadata (and Alembic autogenerate) sees all tables."""

from app.modules.access_control.models import Permission, Role
from app.modules.addresses.models import Address
from app.modules.audit.models import AuditLog
from app.modules.auth.models import PasswordResetToken, RateLimitHit, RefreshToken
from app.modules.cart.models import Cart, CartItem
from app.modules.catalog.models import (
    Brand,
    Category,
    Product,
    ProductAttribute,
    ProductMedia,
    ProductSku,
)
from app.modules.courier_import.models import CourierImport
from app.modules.dispatch.models import DispatchBatch
from app.modules.orders.models import Order, OrderItem, OrderStatusEvent
from app.modules.users.models import User

__all__ = [
    "Address",
    "AuditLog",
    "Brand",
    "Cart",
    "CartItem",
    "Category",
    "CourierImport",
    "DispatchBatch",
    "Order",
    "OrderItem",
    "OrderStatusEvent",
    "PasswordResetToken",
    "Permission",
    "Product",
    "ProductAttribute",
    "ProductMedia",
    "ProductSku",
    "RateLimitHit",
    "RefreshToken",
    "Role",
    "User",
]
