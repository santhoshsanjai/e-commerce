from typing import Annotated

from fastapi import APIRouter, Cookie, Request, Response, status

from app.core.config import get_settings
from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import AppError
from app.core.rate_limit import Attempt, login_limiter
from app.modules.access_control.service import permissions_for
from app.modules.auth import service
from app.modules.auth.schemas import (
    LoginRequest,
    MeResponse,
    PasswordChange,
    ProfileUpdate,
    RegisterRequest,
    TokenResponse,
)
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


def _client_ip(request: Request) -> str:
    # Behind the proxies, uvicorn sets this from X-Forwarded-For, trusting only the proxy
    # addresses in FORWARDED_ALLOW_IPS, so a client can't pick its own address.
    return request.client.host if request.client else "unknown"


def _account_key(email: str) -> str:
    return f"account:{service.normalise_email(email)}"


def _check_rate_limit(request: Request, email: str) -> Attempt:
    """Count a sign-in attempt against the account and against the caller's address.

    The account limit stops password guessing on one account from many addresses; the address
    limit stops one address trying many accounts. Call `_succeeded` when the attempt succeeds, so
    only failed attempts count.
    """
    settings = get_settings()
    attempt = Attempt()
    window = settings.login_rate_limit_window_seconds
    allowed = login_limiter.hit(
        _account_key(email),
        settings.login_rate_limit_attempts,
        window,
        attempt,
    ) and login_limiter.hit(
        f"ip:{_client_ip(request)}", settings.login_ip_rate_limit_attempts, window, attempt
    )
    if not allowed:
        login_limiter.forget(attempt)
        raise AppError(
            "rate_limited",
            "Too many login attempts. Try again later.",
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
    return attempt


def _succeeded(attempt: Attempt, email: str) -> None:
    """The right password clears the account's failures (a typo or two never builds up to a
    lockout). The address keeps its earlier failures, so signing in to your own account can't
    reset a limit you hit guessing other people's."""
    login_limiter.forget(attempt)
    login_limiter.reset(_account_key(email))


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
    attempt = _check_rate_limit(request, data.email)
    tokens = service.login(db, data.email, data.password, UserType.BUYER, request)
    _succeeded(attempt, data.email)
    return _token_response(response, tokens)


@router.post("/staff/login")
def staff_login(
    data: LoginRequest, request: Request, response: Response, db: DbSession
) -> TokenResponse:
    attempt = _check_rate_limit(request, data.email)
    tokens = service.login(db, data.email, data.password, UserType.STAFF, request)
    _succeeded(attempt, data.email)
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


@router.patch("/me")
def update_me(data: ProfileUpdate, user: CurrentUser, db: DbSession) -> MeResponse:
    """Change your own name or phone. Email changes need verification and come later."""
    return _me(service.update_profile(db, user, data))


@router.post("/change-password")
def change_password(
    data: PasswordChange,
    request: Request,
    response: Response,
    user: CurrentUser,
    db: DbSession,
) -> TokenResponse:
    """Signs out every other device and returns fresh tokens for this one."""
    # Shares the login limit, so a stolen access token can't be used to guess the password.
    attempt = _check_rate_limit(request, user.email)
    tokens = service.change_password(db, user, data, request)
    _succeeded(attempt, user.email)
    return _token_response(response, tokens)
