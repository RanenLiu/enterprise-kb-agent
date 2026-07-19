import uuid

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kb_biz.core.auth.jwt import decode_token
from kb_biz.core.exceptions import ForbiddenException, UnauthorizedException
from kb_adapter_postgres.session import get_session
from kb_biz.models.permission import Permission
from kb_biz.models.role import DepartmentRole, RolePermission, UserRole
from kb_biz.models.user import User


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise UnauthorizedException("Missing or invalid Authorization header")

    token = auth_header.removeprefix("Bearer ")
    # Check token blacklist (password change forces re-login)
    try:
        from redis.asyncio import Redis as AsyncRedis
        from kb_biz.config.settings import settings
        _r = AsyncRedis.from_url(settings.redis_url)
        bl = await _r.get(f"token_blacklist:{token}")
        await _r.aclose()
        if bl:
            raise UnauthorizedException("密码已修改，请重新登录")
    except UnauthorizedException:
        raise
    except Exception:
        pass

    payload = decode_token(token)

    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token payload")

    result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or user.status != 1:
        raise UnauthorizedException("User not found or inactive")

    return user


class PermissionChecker:
    """Check that the current user has ALL required permissions.

    Loads permissions from direct user roles and department-inherited roles.
    """

    def __init__(self, required_permissions: list[str]):
        self.required_permissions = required_permissions

    async def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        # Load user's role IDs from direct assignments
        user_role_result = await session.execute(
            select(UserRole.role_id).where(UserRole.user_id == current_user.id)
        )
        role_ids = {r for r in user_role_result.scalars().all()}

        # Add department-inherited roles
        if current_user.dept_id:
            dept_role_result = await session.execute(
                select(DepartmentRole.role_id).where(
                    DepartmentRole.dept_id == current_user.dept_id
                )
            )
            role_ids.update(dept_role_result.scalars().all())

        if not role_ids:
            raise ForbiddenException("No roles assigned")

        # Load permission codes for those roles
        perm_result = await session.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id.in_(role_ids))
        )
        user_permissions = set(perm_result.scalars().all())

        # Check all required permissions are present
        missing = [
            p for p in self.required_permissions if p not in user_permissions
        ]
        if missing:
            raise ForbiddenException(
                f"Missing required permissions: {', '.join(missing)}"
            )

        return current_user


class RoleChecker:
    """Check that the current user has at least one of the allowed roles."""

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        request: Request,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        from kb_biz.models.role import Role

        # Load user's role IDs
        user_role_result = await session.execute(
            select(UserRole.role_id).where(UserRole.user_id == current_user.id)
        )
        role_ids = {r for r in user_role_result.scalars().all()}

        if current_user.dept_id:
            dept_role_result = await session.execute(
                select(DepartmentRole.role_id).where(
                    DepartmentRole.dept_id == current_user.dept_id
                )
            )
            role_ids.update(dept_role_result.scalars().all())

        if not role_ids:
            raise ForbiddenException("No roles assigned")

        # Load role codes
        role_result = await session.execute(
            select(Role.code).where(Role.id.in_(role_ids))
        )
        user_role_codes = set(role_result.scalars().all())

        if not any(r in user_role_codes for r in self.allowed_roles):
            raise ForbiddenException(
                f"Requires one of roles: {', '.join(self.allowed_roles)}"
            )

        return current_user
