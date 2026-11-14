import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, request_id_var
from app.infrastructure.database import SessionLocal
from app.modules.access_control.router import router as access_control_router
from app.modules.addresses.router import router as addresses_router
from app.modules.auth.router import router as auth_router
from app.modules.cart.router import router as cart_router
from app.modules.catalog.router import admin_router as catalog_admin_router
from app.modules.catalog.router import public_router as catalog_public_router
from app.modules.checkout.router import router as checkout_router
from app.modules.dispatch.router import router as dispatch_router
from app.modules.orders.router import admin_router as orders_admin_router
from app.modules.orders.router import buyer_router as orders_buyer_router
from app.modules.users.router import router as users_router

logger = logging.getLogger("app")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    register_exception_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Idempotency-Key"],
    )

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("x-request-id", "")
        rid = incoming if 0 < len(incoming) <= 64 else uuid.uuid4().hex
        token = request_id_var.set(rid)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.get("/health/live", tags=["health"])
    def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"], response_model=None)
    def ready() -> dict[str, str] | JSONResponse:
        try:
            with SessionLocal() as session:
                session.execute(text("SELECT 1"))
        except Exception:
            logger.exception("Readiness check failed")
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return {"status": "ok"}

    api = APIRouter(prefix="/api/v1")
    api.include_router(auth_router)
    api.include_router(users_router)
    api.include_router(access_control_router)
    api.include_router(catalog_public_router)
    api.include_router(catalog_admin_router)
    api.include_router(addresses_router)
    api.include_router(cart_router)
    api.include_router(checkout_router)
    api.include_router(orders_buyer_router)
    api.include_router(dispatch_router)
    api.include_router(orders_admin_router)
    app.include_router(api)
    return app


app = create_app()
