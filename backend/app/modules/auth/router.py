from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response, status

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import AppError
from app.core.rate_limit import login_limiter
from app.modules.access_control.service import permissions_for
from app.modules.auth import service
from app.modules.auth.schemas import LoginRequest, MeResponse, RegisterRequest, TokenResponse
from app.modules.users.models import User, UserType

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, raw: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        raw,
        max_age=settings.refresh_token_ttl_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


def _token_response(response: Response, tokens: service.IssuedTokens) -> TokenResponse:
    _set_refresh_cookie(response, tokens.refresh_token)
    return TokenResponse(access_token=tokens.access_token, expires_in=tokens.expires_in)


def _check_rate_limit(request: Request, email: str) -> None:
    settings = get_settings()
    ip = request.client.host if request.client else "unknown"
    key = f"{ip}:{service.normalise_email(email)}"
    allowed = login_limiter.hit(
        key, settings.login_rate_limit_attempts, settings.login_rate_limit_window_seconds
    )
    if not allowed:
        raise AppError(
            "rate_limited",
            "Too many login attempts. Try again later.",
            status.HTTP_429_TOO_MANY_REQUESTS,
        )


def _me(user: User) -> MeResponse:
    return MeResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        user_type=user.user_type,
        roles=sorted(role.name for role in user.roles),
        permissions=sorted(permissions_for(user)),
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: DbSession) -> MeResponse:
    """Create a buyer account. Staff accounts are created by a Super Admin, never here."""
    return _me(service.register_buyer(db, data))


@router.post("/login")
def buyer_login(
    data: LoginRequest, request: Request, response: Response, db: DbSession
) -> TokenResponse:
    _check_rate_limit(request, data.email)
    tokens = service.login(db, data.email, data.password, UserType.BUYER, request)
    return _token_response(response, tokens)


@router.post("/staff/login")
def staff_login(
    data: LoginRequest, request: Request, response: Response, db: DbSession
) -> TokenResponse:
    _check_rate_limit(request, data.email)
    tokens = service.login(db, data.email, data.password, UserType.STAFF, request)
    return _token_response(response, tokens)


@router.post("/refresh")
def refresh(
    response: Response,
    db: DbSession,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> TokenResponse:
    tokens = service.rotate_refresh_token(db, refresh_token)
    return _token_response(response, tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    db: DbSession,
    refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> None:
    service.logout(db, refresh_token)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


@router.get("/me")
def me(user: CurrentUser) -> MeResponse:
    return _me(user)
