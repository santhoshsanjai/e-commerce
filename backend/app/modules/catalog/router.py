import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status

from app.core.config import get_settings
from app.core.dependencies import DbSession, require_permission
from app.core.exceptions import AppError
from app.infrastructure.storage import ObjectStorage, get_storage
from app.modules.catalog import service
from app.modules.catalog.models import ProductStatus
from app.modules.catalog.schemas import (
    AdminProductListItem,
    AdminProductOut,
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    ProductCard,
    ProductCreate,
    ProductDetail,
    ProductSort,
    ProductUpdate,
)
from app.modules.users.models import User
from app.shared.pagination import Page, PageParams, page_params

Storage = Annotated[ObjectStorage, Depends(get_storage)]
Paging = Annotated[PageParams, Depends(page_params)]

public_router = APIRouter(tags=["catalogue"])
admin_router = APIRouter(prefix="/admin", tags=["admin: catalogue"])


CanViewCategories = Annotated[User, Depends(require_permission("categories.view"))]
CanManageCategories = Annotated[User, Depends(require_permission("categories.manage"))]
CanViewProducts = Annotated[User, Depends(require_permission("products.view"))]
CanCreateProducts = Annotated[User, Depends(require_permission("products.create"))]
CanUpdateProducts = Annotated[User, Depends(require_permission("products.update"))]
CanPublishProducts = Annotated[User, Depends(require_permission("products.publish"))]
CanArchiveProducts = Annotated[User, Depends(require_permission("products.archive"))]


# ---------- Public ----------


@public_router.get("/categories")
def public_categories(db: DbSession) -> list[CategoryOut]:
    return [CategoryOut.model_validate(c) for c in service.list_categories(db, active_only=True)]


@public_router.get("/products")
def public_products(
    db: DbSession,
    storage: Storage,
    params: Paging,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category: Annotated[str | None, Query(max_length=140)] = None,
    sort: ProductSort = ProductSort.NEWEST,
) -> Page[ProductCard]:
    return service.search_products(db, storage, params, q, category, sort)


@public_router.get("/products/{slug}")
def public_product(slug: str, db: DbSession, storage: Storage) -> ProductDetail:
    return service.get_published_by_slug(db, storage, slug)


# ---------- Admin: categories ----------


@admin_router.get("/categories")
def admin_categories(db: DbSession, _: CanViewCategories) -> list[CategoryOut]:
    return [CategoryOut.model_validate(c) for c in service.list_categories(db, active_only=False)]


@admin_router.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: DbSession, _: CanManageCategories) -> CategoryOut:
    return CategoryOut.model_validate(service.create_category(db, data))


@admin_router.patch("/categories/{category_id}")
def update_category(
    category_id: uuid.UUID, data: CategoryUpdate, db: DbSession, _: CanManageCategories
) -> CategoryOut:
    return CategoryOut.model_validate(service.update_category(db, category_id, data))


# ---------- Admin: products ----------


@admin_router.get("/products")
def admin_products(
    db: DbSession,
    storage: Storage,
    params: Paging,
    _: CanViewProducts,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[ProductStatus | None, Query(alias="status")] = None,
) -> Page[AdminProductListItem]:
    return service.list_admin_products(db, storage, params, q, status_filter)


@admin_router.post("/products", status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate,
    request: Request,
    db: DbSession,
    storage: Storage,
    actor: CanCreateProducts,
) -> AdminProductOut:
    return service.to_admin_out(service.create_product(db, data, actor, request), storage)


@admin_router.get("/products/{product_id}")
def admin_product(
    product_id: uuid.UUID, db: DbSession, storage: Storage, _: CanViewProducts
) -> AdminProductOut:
    return service.to_admin_out(service.get_product(db, product_id), storage)


@admin_router.patch("/products/{product_id}")
def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    request: Request,
    db: DbSession,
    storage: Storage,
    actor: CanUpdateProducts,
) -> AdminProductOut:
    product = service.update_product(db, product_id, data, actor, request)
    return service.to_admin_out(product, storage)


@admin_router.post("/products/{product_id}/publish")
def publish_product(
    product_id: uuid.UUID,
    request: Request,
    db: DbSession,
    storage: Storage,
    actor: CanPublishProducts,
) -> AdminProductOut:
    product = service.set_status(db, product_id, ProductStatus.PUBLISHED, actor, request)
    return service.to_admin_out(product, storage)


@admin_router.post("/products/{product_id}/unpublish")
def unpublish_product(
    product_id: uuid.UUID,
    request: Request,
    db: DbSession,
    storage: Storage,
    actor: CanPublishProducts,
) -> AdminProductOut:
    product = service.set_status(db, product_id, ProductStatus.DRAFT, actor, request)
    return service.to_admin_out(product, storage)


@admin_router.post("/products/{product_id}/archive")
def archive_product(
    product_id: uuid.UUID,
    request: Request,
    db: DbSession,
    storage: Storage,
    actor: CanArchiveProducts,
) -> AdminProductOut:
    product = service.set_status(db, product_id, ProductStatus.ARCHIVED, actor, request)
    return service.to_admin_out(product, storage)


@admin_router.post("/products/{product_id}/media", status_code=status.HTTP_201_CREATED)
def upload_image(
    product_id: uuid.UUID,
    db: DbSession,
    storage: Storage,
    actor: CanUpdateProducts,
    file: Annotated[UploadFile, File()],
    alt_text: Annotated[str, Form(max_length=300)] = "",
) -> AdminProductOut:
    limit = get_settings().max_image_bytes
    raw = file.file.read(limit + 1)
    if len(raw) > limit:
        raise AppError(
            "image_too_large",
            f"Images must be {limit // (1024 * 1024)} MB or smaller",
            status.HTTP_413_CONTENT_TOO_LARGE,
        )
    product = service.add_image(db, storage, product_id, raw, alt_text, actor)
    return service.to_admin_out(product, storage)


@admin_router.delete("/products/{product_id}/media/{media_id}")
def delete_media(
    product_id: uuid.UUID,
    media_id: uuid.UUID,
    db: DbSession,
    storage: Storage,
    actor: CanUpdateProducts,
) -> AdminProductOut:
    product = service.remove_media(db, storage, product_id, media_id, actor)
    return service.to_admin_out(product, storage)
