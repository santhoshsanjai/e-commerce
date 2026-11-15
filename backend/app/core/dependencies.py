import uuid
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import NotAuthenticated, PermissionDenied
from app.core.security import decode_access_token
from app.infrastructure.database import get_db
from app.modules.access_control.service import permissions_for
from app.modules.users.models import AUDIENCE_FOR, User, UserType

DbSession = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise NotAuthenticated()
    try:
        claims = decode_access_token(credentials.credentials, ["buyer", "staff"])
        user_id = uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise NotAuthenticated("Invalid or expired token") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active or claims["aud"] != AUDIENCE_FOR[user.user_type]:
        raise NotAuthenticated("Invalid or expired token")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_staff(user: CurrentUser) -> User:
    if user.user_type is not UserType.STAFF:
        raise PermissionDenied()
    return user


CurrentStaff = Annotated[User, Depends(get_current_staff)]


def require_permission(*keys: str) -> Callable[[User], User]:
    """Route dependency: the staff user must hold every listed permission.

    The API is the security authority; the admin UI only hides what this would refuse.
    """

    def checker(user: CurrentStaff) -> User:
        if not set(keys) <= permissions_for(user):
            raise PermissionDenied()
        return user

    return checker
