import logging
import os
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path

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
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.cart.router import router as cart_router
from app.modules.catalog.router import admin_router as catalog_admin_router
from app.modules.catalog.router import public_router as catalog_public_router
from app.modules.checkout.router import router as checkout_router
from app.modules.courier_import.router import router as courier_import_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.dispatch.router import router as dispatch_router
from app.modules.orders.router import admin_router as orders_admin_router
from app.modules.orders.router import buyer_router as orders_buyer_router
from app.modules.reports.router import router as reports_router
from app.modules.users.router import router as users_router

logger = logging.getLogger("app")
access_logger = logging.getLogger("app.access")

# Set at image build time (the git commit), so logs and /health/live show what is running.
APP_VERSION = os.environ.get("APP_VERSION", "dev")


def _expected_db_revision() -> str | None:
    """The newest migration shipped with this code."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    root = Path(__file__).resolve().parent.parent
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    return ScriptDirectory.from_config(config).get_current_head()


EXPECTED_DB_REVISION = _expected_db_revision()


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
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            if not request.url.path.startswith("/health/"):
                # One structured line per request: what the 5xx and latency alarms count.
                access_logger.info(
                    "request",
                    extra={
                        "fields": {
                            "request_id": rid,
                            "method": request.method,
                            "path": request.url.path,
                            "status": status_code,
                            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                            "client_ip": request.client.host if request.client else None,
                        }
                    },
                )
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api/"):
            # JSON and file downloads only: nothing here should run scripts, be framed or be
            # cached by browsers or shared proxies (responses carry personal data).
            response.headers["Content-Security-Policy"] = (
                "default-src 'none'; frame-ancestors 'none'"
            )
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.get("/health/live", tags=["health"])
    def live() -> dict[str, str]:
        """The process is up. Container health checks use this; it never touches the database."""
        return {"status": "ok", "version": APP_VERSION}

    @app.get("/health/ready", tags=["health"], response_model=None)
    def ready() -> dict[str, str] | JSONResponse:
        """Ready for traffic: the database answers and its schema matches this code. The load
        balancer sends requests only to ready instances, so a deploy whose migration didn't run
        never takes traffic."""
        try:
            with SessionLocal() as session:
                db_revision = session.scalar(text("SELECT version_num FROM alembic_version"))
        except Exception:
            logger.exception("Readiness check failed")
            return JSONResponse({"status": "unavailable"}, status_code=503)
        if db_revision != EXPECTED_DB_REVISION:
            logger.error(
                "Database schema is at %s, this code needs %s", db_revision, EXPECTED_DB_REVISION
            )
            return JSONResponse(
                {"status": "unavailable", "reason": "schema_mismatch"}, status_code=503
            )
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
    api.include_router(courier_import_router)
    api.include_router(dashboard_router)
    api.include_router(audit_router)
    api.include_router(reports_router)
    api.include_router(orders_admin_router)
    app.include_router(api)
    return app


app = create_app()
