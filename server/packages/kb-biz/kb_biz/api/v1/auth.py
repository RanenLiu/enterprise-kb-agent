from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kb_biz.core.auth.deps import get_current_user
from kb_biz.core.auth.jwt import create_access_token, create_refresh_token, decode_token
from kb_biz.core.auth.password import hash_password, verify_password
from kb_biz.core.captcha import generate_code as generate_captcha_code, render_svg
from kb_biz.core.exceptions import UnauthorizedException, ValidationException
from kb_biz.core.operation_log import record_operation
from kb_biz.core.redis import get_redis
from kb_biz.core.user_cache import get_cached_user, set_cached_user
from kb_adapter_postgres.session import async_session_factory, get_session
from kb_biz.models.department import Department
from kb_biz.models.tenant import Tenant
from kb_biz.models.log import LoginLog
from kb_biz.models.menu import Menu, RoleMenu
from kb_biz.models.permission import Permission
from kb_biz.models.role import DepartmentRole, Role, RolePermission, UserRole
from kb_biz.models.user import User
from kb_biz.schemas.auth import (
    CaptchaResponse,
    ChangePasswordRequest,
    LoginRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    RefreshRequest,
    TokenResponse,
)
from kb_biz.schemas.common import Response

router = APIRouter(prefix="/auth", tags=["auth"])


def _record_failed_login(username: str, reason: str, ip: str | None, ua: str | None,
                         user_id: str | None = None, display_name: str | None = None,
                         tenant_id: str | None = None, dept_id: str | None = None) -> None:
    """Record a failed login log with a separate session, independent of the current transaction."""

    async def _do():
        async with async_session_factory() as s:
            s.add(LoginLog(user_id=user_id, user_name=display_name or username, result="failure",
                           failure_reason=reason, login_type="password", ip_address=ip, user_agent=ua,
                           tenant_id=tenant_id, dept_id=dept_id,
                           created_at=datetime.now(timezone.utc)))
            await s.commit()
        # Increment failure counter for captcha enforcement
        if ip:
            try:
                from kb_biz.core.redis import get_redis
                redis = await get_redis()
                if redis:
                    await redis.incr(f"login_failures:{ip}")
                    await redis.expire(f"login_failures:{ip}", 1800)  # 30 min TTL
            except Exception:
                pass
    asyncio.ensure_future(_do())


def _update_last_login(session: AsyncSession, user_id: str) -> None:
    """Update last_login_at asynchronously, non-blocking."""

    async def _do():
        async with async_session_factory() as s:
            u = await s.get(User, uuid.UUID(user_id))
            if u:
                u.last_login_at = datetime.now(timezone.utc)
                s.add(u)
                await s.commit()
    asyncio.ensure_future(_do())


@router.get("/captcha", response_model=Response[CaptchaResponse])
async def captcha():
    """Generate a captcha image (SVG) and return it with a token."""
    redis = await get_redis()
    code = generate_captcha_code()
    token = str(uuid.uuid4())
    svg = render_svg(code)
    if redis:
        await redis.setex(f"captcha:{token}", 300, code)  # 5 min TTL
    return Response(data=CaptchaResponse(token=token, svg=svg))


async def _verify_captcha(token: str | None, code: str | None, ip: str | None = None) -> None:
    """Verify captcha token and code. Requires captcha if previous failures exist."""
    redis = await get_redis()
    if redis and ip:
        fail_key = f"login_failures:{ip}"
        failures = await redis.get(fail_key)
        if failures and int(failures) > 0:
            # Previous failure exists, captcha required
            if not token or not code:
                raise ValidationException("请完成验证码验证")
        else:
            # No prior failures, skip captcha for this attempt
            if token is None and code is None:
                return

    if not token or not code:
        return  # No captcha data, skip check

    if not redis:
        return

    key = f"captcha:{token}"
    expected = await redis.get(key)
    await redis.delete(key)
    if not expected or expected.lower() != code.lower():
        raise ValidationException("验证码错误")


@router.post("/login", response_model=Response[TokenResponse])
async def login(request: LoginRequest, http_request: Request, session: AsyncSession = Depends(get_session)):
    ip = http_request.client.host if http_request.client else None
    await _verify_captcha(request.captcha_token, request.captcha_code, ip)
    ua = http_request.headers.get("user-agent")
    username = request.username

    # 1. Try cache first
    cached = await get_cached_user(username)
    if cached:
        # If tenant_code provided, verify cached user belongs to that tenant
        if request.tenant_code and cached.get("tenant_code") != request.tenant_code:
            cached = None  # Wrong tenant, fall through to DB query
    if cached:
        pw_ok = verify_password(request.password, cached.get("password_hash", ""))
        if not pw_ok:
            _record_failed_login(username, "invalid_password", ip, ua,
                                 cached["user_id"], cached.get("display_name"),
                                 cached.get("tenant_id"), cached.get("dept_id"))
            raise UnauthorizedException("用户名或密码错误")
        if cached.get("status") != 1:
            raise UnauthorizedException("Account is inactive or locked")
        # Build token from cached data
        token = TokenResponse(
            access_token=create_access_token(uuid.UUID(cached["user_id"]), cached.get("dept_id")),
            refresh_token=create_refresh_token(uuid.UUID(cached["user_id"])),
            theme_prefs=cached.get("theme_prefs"),
            username=cached.get("username", ""),
            display_name=cached.get("display_name", ""),
        )
        # Update last_login_at in background
        _update_last_login(session, cached["user_id"])
        # Reset failure counter
        if ip:
            try:
                redis = await get_redis()
                if redis:
                    await redis.delete(f"login_failures:{ip}")
            except Exception:
                pass
        return Response(data=token)

    # 2. Cache miss — query DB
    # 支持邮箱登录：输入包含 @ 时按 email 查找
    is_email = "@" in username
    if is_email:
        if request.tenant_code:
            result = await session.execute(
                select(User).join(Tenant, User.tenant_id == Tenant.id)
                .where(User.email == username, Tenant.code == request.tenant_code)
            )
            user = result.scalar_one_or_none()
        else:
            result = await session.execute(
                select(User).where(User.email == username)
            )
            users = result.scalars().all()
            if len(users) > 1:
                raise UnauthorizedException("该邮箱存在多个账户，请指定租户编码")
            user = users[0] if users else None
    elif request.tenant_code:
        result = await session.execute(
            select(User).join(Tenant, User.tenant_id == Tenant.id)
            .where(User.username == username, Tenant.code == request.tenant_code)
        )
        user = result.scalar_one_or_none()
    else:
        # No tenant_code: check for duplicate usernames across tenants
        result = await session.execute(
            select(User).where(User.username == username)
        )
        users = result.scalars().all()
        if len(users) > 1:
            raise UnauthorizedException("用户名存在多个，请指定租户编码")
        user = users[0] if users else None

    if not user:
        _record_failed_login(username, "invalid_password", ip, ua)
        raise UnauthorizedException("用户名或密码错误")
    if not verify_password(request.password, user.password_hash):
        _record_failed_login(username, "invalid_password", ip, ua,
                             str(user.id), user.display_name,
                             str(user.tenant_id) if user.tenant_id else None,
                             str(user.dept_id) if user.dept_id else None)
        raise UnauthorizedException("用户名或密码错误")

    if user.status != 1:
        _record_failed_login(username, "inactive", ip, ua, str(user.id), user.display_name,
                             str(user.tenant_id) if user.tenant_id else None,
                             str(user.dept_id) if user.dept_id else None)
        raise UnauthorizedException("Account is inactive or locked")

    user.last_login_at = datetime.now(timezone.utc)
    session.add(user)
    await session.flush()
    session.add(LoginLog(user_id=user.id, user_name=user.display_name, tenant_id=user.tenant_id, dept_id=user.dept_id, result="success", login_type="password", ip_address=ip, user_agent=ua, created_at=datetime.now(timezone.utc)))

    theme_prefs = user.theme_prefs or {"theme": "light", "accent": "blue"}

    # Cache user for next login
    # Resolve tenant_code for cache
    user_tenant_code = None
    if user.tenant_id:
        tenant_row = await session.execute(
            select(Tenant.code).where(Tenant.id == user.tenant_id)
        )
        user_tenant_code = tenant_row.scalar_one_or_none()
    await set_cached_user(username, {
        "user_id": str(user.id),
        "password_hash": user.password_hash,
        "display_name": user.display_name,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "tenant_code": user_tenant_code,
        "dept_id": str(user.dept_id) if user.dept_id else None,
        "status": user.status,
        "theme_prefs": theme_prefs,
    })

    dept_id = str(user.dept_id) if user.dept_id else None
    # Reset failure counter
    if ip:
        try:
            redis = await get_redis()
            if redis:
                await redis.delete(f"login_failures:{ip}")
        except Exception:
            pass
    return Response(
        data=TokenResponse(
            access_token=create_access_token(user.id, dept_id),
            refresh_token=create_refresh_token(user.id),
            theme_prefs=theme_prefs,
            username=user.username,
            display_name=user.display_name,
        )
    )

@router.post("/refresh", response_model=Response[TokenResponse])
async def refresh(request: RefreshRequest, session: AsyncSession = Depends(get_session)):
    payload = decode_token(request.refresh_token)
    if payload.get("type") != "refresh":
        raise UnauthorizedException("Invalid refresh token")

    user_id = payload.get("sub")
    result = await session.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or user.status != 1:
        raise UnauthorizedException("User not found or inactive")

    dept_id = str(user.dept_id) if user.dept_id else None
    return Response(
        data=TokenResponse(
            access_token=create_access_token(user.id, dept_id),
            refresh_token=create_refresh_token(user.id),
        )
    )


@router.post("/logout", response_model=Response[None])
async def logout(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await record_operation(session, current_user, "logout", "auth", str(current_user.id), current_user.display_name or current_user.username)
    return Response(data=None)


@router.get("/profile", response_model=Response[ProfileResponse])
async def get_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    dept_name = None
    if current_user.dept_id:
        result = await session.execute(
            select(Department).where(Department.id == current_user.dept_id)
        )
        dept = result.scalar_one_or_none()
        dept_name = dept.name if dept else None

    # Load roles: direct (user_roles) + department-inherited (department_roles)

    direct_role_ids = select(UserRole.role_id).where(UserRole.user_id == current_user.id)
    if current_user.dept_id:
        dept_role_ids = select(DepartmentRole.role_id).where(DepartmentRole.dept_id == current_user.dept_id)
        role_ids = select(Role).where(Role.id.in_(direct_role_ids.union(dept_role_ids)))
    else:
        role_ids = select(Role).where(Role.id.in_(direct_role_ids))
    role_rows = await session.execute(role_ids)
    roles = role_rows.scalars().all()
    role_codes = [r.code for r in roles]

    perm_rows = await session.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id.in_([r.id for r in roles]))
        .distinct()
    )
    permissions = [p.code for p in perm_rows.scalars().all()]

    return Response(
        data=ProfileResponse(
            id=str(current_user.id),
            username=current_user.username,
            display_name=current_user.display_name,
            avatar=current_user.avatar,
            email=current_user.email,
            phone=current_user.phone,
            dept_id=str(current_user.dept_id) if current_user.dept_id else None,
            dept_name=dept_name,
            roles=role_codes,
            permissions=permissions,
            theme_prefs=current_user.theme_prefs or {"theme": "light", "accent": "blue"},
        )
    )


@router.put("/profile", response_model=Response[ProfileResponse])
async def update_profile(
    request: ProfileUpdateRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    changes = []
    if request.display_name is not None:
        if current_user.display_name != request.display_name:
            changes.append(f"name:{current_user.display_name}→{request.display_name}")
        current_user.display_name = request.display_name
    if request.email is not None:
        if current_user.email != request.email:
            changes.append(f"email:{current_user.email}→{request.email}")
        current_user.email = request.email
    if request.phone is not None:
        if current_user.phone != request.phone:
            changes.append(f"phone:{current_user.phone}→{request.phone}")
        current_user.phone = request.phone
    if request.avatar is not None:
        changes.append("avatar:updated")
        current_user.avatar = request.avatar
    if request.theme_prefs is not None:
        changes.append("theme:updated")
        current_user.theme_prefs = request.theme_prefs

    session.add(current_user)
    detail = {"changes": changes} if changes else None
    ip = http_request.client.host if http_request.client else None
    await record_operation(session, current_user, "update", "profile", str(current_user.id), current_user.display_name or current_user.username, detail=detail, ip_address=ip)
    return await get_profile(current_user, session)


@router.put("/password", response_model=Response[None])
async def change_password(
    request: ChangePasswordRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not verify_password(request.old_password, current_user.password_hash):
        raise ValidationException("Old password is incorrect")

    current_user.password_hash = hash_password(request.new_password)
    session.add(current_user)
    ip = http_request.client.host if http_request.client else None
    await record_operation(session, current_user, "update", "password", str(current_user.id), current_user.username, detail={"note": "password_updated"}, ip_address=ip)
    # Invalidate Redis cache so updated password takes effect immediately
    try:
        from kb_biz.core.user_cache import invalidate_user
        await invalidate_user(str(current_user.id))
    except Exception:
        pass
    # Blacklist current token to force re-login
    try:
        from redis.asyncio import Redis as AsyncRedis
        from kb_biz.config.settings import settings
        r = AsyncRedis.from_url(settings.redis_url)
        auth_header = http_request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ") if auth_header.startswith("Bearer ") else ""
        if token:
            ttl = 3600  # blacklist for 1 hour (typical token lifetime)
            await r.setex(f"token_blacklist:{token}", ttl, "1")
        await r.aclose()
    except Exception:
        pass
    return Response(data=None)


# ──────────────────────────────────────────────
# User Menus (for dynamic sidebar)
# ──────────────────────────────────────────────

@router.get("/menus", response_model=Response[list[dict]])
async def get_user_menus(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Return menu tree filtered by current user's roles, cached in Redis."""
    cache_key = f"user_menus:{current_user.id}"

    # Try Redis cache
    try:
        from kb_biz.core.redis import get_redis
        r = await get_redis()
        if r:
            cached = await r.get(cache_key)
            if cached:
                import json
                return Response(data=json.loads(cached))
    except Exception:
        pass

    # Collect role IDs: direct + department-inherited
    role_ids = select(UserRole.role_id).where(UserRole.user_id == current_user.id)
    if current_user.dept_id:
        dept_role_ids = select(DepartmentRole.role_id).where(DepartmentRole.dept_id == current_user.dept_id)
        role_ids = role_ids.union(dept_role_ids)

    # Get menu IDs from role_menus
    menu_id_rows = await session.execute(
        select(RoleMenu.menu_id).where(RoleMenu.role_id.in_(role_ids))
    )
    allowed_menu_ids = {r[0] for r in menu_id_rows.all()}

    # Get all menus and user's permissions
    result = await session.execute(select(Menu).order_by(Menu.sort_order))
    all_menus = result.scalars().all()

    # Load user's actual permission codes for cross-check
    perm_rows = await session.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id.in_(role_ids))
        .distinct()
    )
    user_perms = {r[0] for r in perm_rows.all()}

    def _build_tree(parent_id: uuid.UUID | None = None) -> list[dict]:
        nodes = []
        for m in all_menus:
            if m.parent_id == parent_id and m.id in allowed_menu_ids:
                if m.permission_code and m.permission_code not in user_perms:
                    continue
                children = _build_tree(m.id)
                if not m.path and not children:
                    continue
                nodes.append({
                    "id": str(m.id),
                    "parent_id": str(m.parent_id) if m.parent_id else None,
                    "name": m.name,
                    "path": m.path,
                    "icon": m.icon,
                    "permission_code": m.permission_code,
                    "sort_order": m.sort_order,
                    "hidden": m.hidden,
                    "children": children,
                })
        nodes.sort(key=lambda x: x["sort_order"])
        return nodes

    tree = _build_tree()

    # Cache in Redis (5 min TTL)
    try:
        import json
        if r:
            await r.setex(cache_key, 300, json.dumps(tree))
    except Exception:
        pass

    return Response(data=tree)
