from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_var


class AppError(Exception):
    """A business error with a stable machine-readable code."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


class NotAuthenticated(AppError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__("not_authenticated", message, status.HTTP_401_UNAUTHORIZED)


class PermissionDenied(AppError):
    def __init__(self, message: str = "You do not have permission for this action") -> None:
        super().__init__("permission_denied", message, status.HTTP_403_FORBIDDEN)


def _body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id_var.get(),
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            _body(exc.code, exc.message, exc.details), exc.status_code, headers=headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()
        ]
        return JSONResponse(
            _body("validation_error", "Request validation failed", details),
            status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    @app.exception_handler(DataError)
    async def data_error_handler(_: Request, exc: DataError) -> JSONResponse:
        # A value the database can't store, such as text with a NUL character (%00) in a search
        # or a form. It's bad input, not a server fault, and the database's text stays private.
        return JSONResponse(
            _body("invalid_input", "The request contains characters or values that can't be used"),
            status.HTTP_400_BAD_REQUEST,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(_body("http_error", str(exc.detail)), exc.status_code)
