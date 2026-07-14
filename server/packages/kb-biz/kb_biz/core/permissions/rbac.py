from __future__ import annotations

from enum import Enum


class BuiltInRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    DEPT_ADMIN = "dept_admin"
    DEPT_EDITOR = "dept_editor"
    DEPT_VIEWER = "dept_viewer"


class BuiltInPermission(str, Enum):
    # Document
    DOCUMENT_CREATE = "document.create"
    DOCUMENT_READ = "document.read"
    DOCUMENT_UPDATE = "document.update"
    DOCUMENT_DELETE = "document.delete"
    DOCUMENT_REINDEX = "document.reindex"

    # Department
    DEPT_CREATE = "department.create"
    DEPT_READ = "department.read"
    DEPT_UPDATE = "department.update"
    DEPT_DELETE = "department.delete"

    # User
    USER_CREATE = "user.create"
    USER_READ = "user.read"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"

    # Role
    ROLE_CREATE = "role.create"
    ROLE_READ = "role.read"
    ROLE_UPDATE = "role.update"
    ROLE_DELETE = "role.delete"

    # Menu
    MENU_CREATE = "menu.create"
    MENU_READ = "menu.read"
    MENU_UPDATE = "menu.update"
    MENU_DELETE = "menu.delete"

    # System
    SYSTEM_TENANT = "system.tenant"
    SYSTEM_CONFIG = "system.config"
    SYSTEM_LOGS = "system.logs"
    SYSTEM_MONITOR = "system.monitor"

    # LLM Config
    LLM_CONFIG_READ = "llm_config.read"
    LLM_CONFIG_UPDATE = "llm_config.update"

    # Project
    PROJECT_CREATE = "project.create"
    PROJECT_READ = "project.read"
    PROJECT_UPDATE = "project.update"
    PROJECT_DELETE = "project.delete"

    # Chat
    CHAT_ACCESS = "chat.access"


# Permission group definitions
PERMISSION_GROUPS: dict[str, str] = {
    "document": "知识库管理",
    "department": "部门管理",
    "user": "用户管理",
    "role": "角色管理",
    "menu": "菜单管理",
    "system": "系统设置",
    "llm_config": "模型配置",
    "chat": "智能问答",
    "tenant": "租户管理",
    "project": "项目管理",
}

# Role to permission mapping
ROLE_PERMISSIONS: dict[BuiltInRole, list[BuiltInPermission]] = {
    BuiltInRole.SUPER_ADMIN: list(BuiltInPermission),
    BuiltInRole.TENANT_ADMIN: [
        BuiltInPermission.DOCUMENT_CREATE,
        BuiltInPermission.DOCUMENT_READ,
        BuiltInPermission.DOCUMENT_UPDATE,
        BuiltInPermission.DOCUMENT_DELETE,
        BuiltInPermission.DOCUMENT_REINDEX,
        BuiltInPermission.DEPT_CREATE,
        BuiltInPermission.DEPT_READ,
        BuiltInPermission.DEPT_UPDATE,
        BuiltInPermission.DEPT_DELETE,
        BuiltInPermission.USER_CREATE,
        BuiltInPermission.USER_READ,
        BuiltInPermission.USER_UPDATE,
        BuiltInPermission.USER_DELETE,
        BuiltInPermission.ROLE_CREATE,
        BuiltInPermission.ROLE_READ,
        BuiltInPermission.ROLE_UPDATE,
        BuiltInPermission.ROLE_DELETE,
        BuiltInPermission.MENU_CREATE,
        BuiltInPermission.MENU_READ,
        BuiltInPermission.MENU_UPDATE,
        BuiltInPermission.MENU_DELETE,
        BuiltInPermission.SYSTEM_CONFIG,
        BuiltInPermission.SYSTEM_LOGS,
        BuiltInPermission.LLM_CONFIG_READ,
        BuiltInPermission.LLM_CONFIG_UPDATE,
        BuiltInPermission.PROJECT_CREATE,
        BuiltInPermission.PROJECT_READ,
        BuiltInPermission.PROJECT_UPDATE,
        BuiltInPermission.PROJECT_DELETE,
        BuiltInPermission.CHAT_ACCESS,
    ],
    BuiltInRole.DEPT_ADMIN: [
        BuiltInPermission.DOCUMENT_CREATE,
        BuiltInPermission.DOCUMENT_READ,
        BuiltInPermission.DOCUMENT_UPDATE,
        BuiltInPermission.DOCUMENT_DELETE,
        BuiltInPermission.DOCUMENT_REINDEX,
        BuiltInPermission.DEPT_READ,
        BuiltInPermission.USER_READ,
        BuiltInPermission.USER_CREATE,
        BuiltInPermission.USER_UPDATE,
        BuiltInPermission.USER_DELETE,
        BuiltInPermission.ROLE_READ,
        BuiltInPermission.CHAT_ACCESS,
        BuiltInPermission.MENU_READ,
        BuiltInPermission.SYSTEM_CONFIG,
        BuiltInPermission.SYSTEM_LOGS,
        BuiltInPermission.PROJECT_CREATE,
        BuiltInPermission.PROJECT_READ,
        BuiltInPermission.PROJECT_UPDATE,
        BuiltInPermission.PROJECT_DELETE,
    ],
    BuiltInRole.DEPT_EDITOR: [
        BuiltInPermission.DOCUMENT_CREATE,
        BuiltInPermission.DOCUMENT_READ,
        BuiltInPermission.DOCUMENT_UPDATE,
        BuiltInPermission.DOCUMENT_DELETE,
        BuiltInPermission.DOCUMENT_REINDEX,
        BuiltInPermission.PROJECT_READ,
        BuiltInPermission.CHAT_ACCESS,
    ],
    BuiltInRole.DEPT_VIEWER: [
        BuiltInPermission.DOCUMENT_READ,
        BuiltInPermission.PROJECT_READ,
        BuiltInPermission.CHAT_ACCESS,
    ],
}
