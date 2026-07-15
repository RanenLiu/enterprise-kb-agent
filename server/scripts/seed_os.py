"""Open source edition seed script: permissions, basic roles, basic menus, admin user.

Usage:
    python -m scripts.seed_os
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from kb_biz.core.permissions.rbac import (
    PERMISSION_GROUPS,
    ROLE_PERMISSIONS,
    BuiltInPermission,
    BuiltInRole,
)
from kb_biz.core.auth.password import hash_password
from kb_adapter_postgres.session import async_session_factory
from kb_biz.models.menu import Menu, RoleMenu
from kb_biz.models.permission import Permission
from kb_biz.models.role import Role, RolePermission
from kb_biz.models.role import UserRole
from kb_biz.models.user import User

logger = logging.getLogger(__name__)


async def seed_permissions(session: AsyncSession) -> dict[str, Permission]:
    """Insert all built-in permissions if they do not already exist."""
    from sqlalchemy import select
    result: dict[str, Permission] = {}
    for perm in BuiltInPermission:
        code = perm.value
        existing = await session.execute(
            select(Permission).where(Permission.code == code)
        )
        db_perm = existing.scalar_one_or_none()
        group = "system"
        for g in PERMISSION_GROUPS:
            if code.startswith(g):
                group = PERMISSION_GROUPS[g]
                break
        if db_perm is None:
            db_perm = Permission(
                code=code,
                name=perm.name,
                group=group,
                description="",
            )
            session.add(db_perm)
        elif db_perm.group != group:
            # Fix pre-existing permissions with wrong group
            db_perm.group = group
            session.add(db_perm)
        result[code] = db_perm
    await session.commit()
    logger.info("Seeded %d permissions", len(result))
    return result


# 开源版角色：租户管理员为最高角色，无超级管理员（单租户模式）
OPEN_SOURCE_ROLES = [
    BuiltInRole.TENANT_ADMIN,
    BuiltInRole.DEPT_ADMIN,
    BuiltInRole.DEPT_EDITOR,
    BuiltInRole.DEPT_VIEWER,
]
ROLE_NAMES_CN = {
    BuiltInRole.TENANT_ADMIN: "管理员",
    BuiltInRole.DEPT_ADMIN: "部门管理员",
    BuiltInRole.DEPT_EDITOR: "部门编辑者",
    BuiltInRole.DEPT_VIEWER: "部门查看者",
}
ROLE_DESCRIPTIONS = {
    BuiltInRole.TENANT_ADMIN: "管理用户、部门、知识库和系统配置",
    BuiltInRole.DEPT_ADMIN: "管理本部门的知识库和用户",
    BuiltInRole.DEPT_EDITOR: "可上传、编辑、删除文档，使用智能问答",
    BuiltInRole.DEPT_VIEWER: "仅可查看文档和使用智能问答",
}


async def seed_roles(session: AsyncSession, perm_map: dict[str, Permission]) -> None:
    """Seed built-in roles with their permission assignments."""
    for role_enum in OPEN_SOURCE_ROLES:
        existing = await session.execute(
            select(Role).where(Role.code == role_enum.value)
        )
        role = existing.scalar_one_or_none()
        if role is None:
            role = Role(
                name=ROLE_NAMES_CN.get(role_enum, role_enum.name.replace("_", " ").title()),
                code=role_enum.value,
                description=ROLE_DESCRIPTIONS.get(role_enum, ""),
                is_system=True,
            )
            session.add(role)
            await session.flush()

        # Sync permissions for this role
        role_perms = ROLE_PERMISSIONS.get(role_enum, [])
        existing_rp = await session.execute(
            select(RolePermission).where(RolePermission.role_id == role.id)
        )
        existing_ids = {rp.permission_id for rp in existing_rp.scalars().all()}
        target_ids = {perm_map[p.value].id for p in role_perms if p.value in perm_map}
        for pid in target_ids - existing_ids:
            session.add(RolePermission(role_id=role.id, permission_id=pid))

    await session.commit()
    logger.info("Seeded %d roles", len(BuiltInRole))


async def seed_menus(session: AsyncSession) -> None:
    """Seed basic menus for open source edition — no enterprise items."""
    await session.execute(delete(RoleMenu))
    await session.execute(delete(Menu))

    menu_items = [
        Menu(name="首页", path="/", icon="Home", permission_code=None, sort_order=0),
        Menu(name="智能问答", path="/chat", icon="MessageSquare", permission_code="chat.access", sort_order=1),
        Menu(name="知识库", path="/knowledge", icon="Database", permission_code="document.read", sort_order=2),
        Menu(name="操作日志", path="/admin/logs", icon="FileText", permission_code="system.logs", sort_order=3),
    ]
    session.add_all(menu_items)
    await session.flush()

    sys_mgmt = Menu(name="系统管理", icon="Settings", sort_order=4)
    session.add(sys_mgmt)
    await session.flush()

    sys_children = [
        Menu(name="部门管理", path="/admin/departments", icon="Building2", permission_code="department.read", parent_id=sys_mgmt.id, sort_order=0),
        Menu(name="角色管理", path="/admin/roles", icon="Shield", permission_code="role.read", parent_id=sys_mgmt.id, sort_order=1),
        Menu(name="用户管理", path="/admin/users", icon="Users", permission_code="user.read", parent_id=sys_mgmt.id, sort_order=2),
        Menu(name="模型配置", path="/admin/models", icon="Cpu", permission_code="llm_config.read", parent_id=sys_mgmt.id, sort_order=3),
        Menu(name="系统公告", path="/admin/announcements", icon="Megaphone", permission_code=None, parent_id=sys_mgmt.id, sort_order=4),
        Menu(name="系统设置", path="/admin/settings", icon="Settings", permission_code="system.config", parent_id=sys_mgmt.id, sort_order=5),
    ]
    session.add_all(sys_children)
    all_menus = menu_items + [sys_mgmt] + sys_children

    await session.commit()

    # Assign all menus to admin role
    admin_role = await session.execute(
        select(Role).where(Role.code == BuiltInRole.TENANT_ADMIN.value)
    )
    admin_role = admin_role.scalar_one_or_none()
    if admin_role:
        for m in all_menus:
            session.add(RoleMenu(role_id=admin_role.id, menu_id=m.id))

    # Assign menus per-role
    dept_admin_menus = [menu_items[0], menu_items[1], menu_items[2], menu_items[3], sys_mgmt] + [sys_children[0], sys_children[2], sys_children[4], sys_children[5]]  # 部门管理,用户管理,系统公告,系统设置
    dept_editor_menus = [menu_items[0], menu_items[1], menu_items[2], menu_items[3]]
    dept_viewer_menus = [menu_items[0], menu_items[1]]

    for role_enum in BuiltInRole:
        role = await session.execute(
            select(Role).where(Role.code == role_enum.value)
        )
        role = role.scalar_one_or_none()
        if not role:
            continue
        if role_enum == BuiltInRole.TENANT_ADMIN:
            continue  # already assigned above
        if role_enum == BuiltInRole.DEPT_ADMIN:
            menus = dept_admin_menus
        elif role_enum == BuiltInRole.DEPT_EDITOR:
            menus = dept_editor_menus
        elif role_enum == BuiltInRole.DEPT_VIEWER:
            menus = dept_viewer_menus
        else:
            continue
        for m in menus:
            session.add(RoleMenu(role_id=role.id, menu_id=m.id))

    await session.commit()
    logger.info("Seeded open source menus")


async def seed_default_department(session: AsyncSession, tenant_id: uuid.UUID) -> None:
    """No-op: global department no longer needed (chunks.dept_id now nullable)."""


async def seed_default_tenant(session: AsyncSession) -> uuid.UUID:
    """Create default single tenant (id=1) for open source edition."""
    from kb_biz.models.tenant import Tenant
    # Check if any tenant exists
    existing = await session.execute(select(Tenant).limit(1))
    tenant = existing.scalar_one_or_none()
    if tenant is None:
        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            name="Default",
            code="default",
            status=1,
            milvus_partition="",
        )
        session.add(tenant)
        await session.flush()
        logger.info(f"Created default tenant ({tenant_id})")
    else:
        tenant_id = tenant.id
    return tenant_id


async def seed_admin(session: AsyncSession) -> None:
    """Create default admin user."""
    tenant_id = await seed_default_tenant(session)
    existing = await session.execute(
        select(User).where(User.username == "admin")
    )
    if existing.scalar_one_or_none():
        logger.info("Admin user already exists, skipping")
        return

    admin_user = User(
        username="admin",
        password_hash=hash_password("admin123"),
        display_name="系统管理员",
        tenant_id=tenant_id,
    )
    session.add(admin_user)
    await session.flush()

    admin_role = await session.execute(
        select(Role).where(Role.code == BuiltInRole.TENANT_ADMIN.value)
    )
    admin_role = admin_role.scalar_one_or_none()
    if admin_role:
        session.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))

    await session.commit()
    logger.info("Seeded admin user: admin / admin123")


async def main():
    logging.basicConfig(level=logging.INFO)
    async with async_session_factory() as session:
        perm_map = await seed_permissions(session)
        await seed_roles(session, perm_map)
        await seed_menus(session)
        tenant_id = await seed_default_tenant(session)
        await seed_default_department(session, tenant_id)
        await seed_admin(session)
    logger.info("Seed complete")


if __name__ == "__main__":
    asyncio.run(main())
