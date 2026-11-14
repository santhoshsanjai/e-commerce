from app.modules.users.models import User, UserType


def permissions_for(user: User) -> set[str]:
    """Union of permissions across all of the user's roles. Buyers never hold admin permissions."""
    if user.user_type is not UserType.STAFF:
        return set()
    return {perm.key for role in user.roles for perm in role.permissions}
