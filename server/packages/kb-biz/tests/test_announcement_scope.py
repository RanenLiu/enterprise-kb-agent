"""Tests for announcement scope assignment based on user roles.

⚠️ Regression prevention:
- dept_admin 只能管理本部门公告，跨部门禁止 (test_dept_admin_can_access_own_dept_only)
- 空角色不再有 dept 权限 (test_empty_roles_cannot_manage)
- list_announcements 的 scope 过滤必须独立于 show_all 参数
  (相关代码: list_announcements 中 if not is_super: 的条件)
"""

from __future__ import annotations

import uuid
from kb_biz.api.v1.admin import _check_announcement_scope_access, _determine_announcement_scope


DEPT_ID_A = uuid.uuid4()
DEPT_ID_B = uuid.uuid4()


class TestDetermineAnnouncementScope:
    def test_super_admin_scope(self):
        """super_admin → system scope."""
        assert _determine_announcement_scope(["super_admin"]) == "system"

    def test_tenant_admin_scope(self):
        """tenant_admin → tenant scope."""
        assert _determine_announcement_scope(["tenant_admin"]) == "tenant"

    def test_dept_admin_scope(self):
        """dept_admin → dept scope."""
        assert _determine_announcement_scope(["dept_admin"]) == "dept"

    def test_dept_editor_scope(self):
        """dept_editor → dept scope (fallback for any non-super/tenant role)."""
        assert _determine_announcement_scope(["dept_editor"]) == "dept"

    def test_dept_viewer_scope(self):
        """dept_viewer → dept scope."""
        assert _determine_announcement_scope(["dept_viewer"]) == "dept"

    def test_multiple_roles_super_admin_wins(self):
        """When user has multiple roles, super_admin takes priority."""
        codes = ["dept_admin", "super_admin"]
        assert _determine_announcement_scope(codes) == "system"

    def test_multiple_roles_tenant_admin_wins(self):
        """When user has multiple roles, tenant_admin takes priority if no super_admin."""
        codes = ["dept_admin", "tenant_admin"]
        assert _determine_announcement_scope(codes) == "tenant"

    def test_empty_role_codes_defaults_to_dept(self):
        """Empty role list → dept scope."""
        assert _determine_announcement_scope([]) == "dept"

    def test_unknown_role_defaults_to_dept(self):
        """Unknown role code → dept scope."""
        assert _determine_announcement_scope(["some_random_role"]) == "dept"


class TestCheckAnnouncementScopeAccess:
    def test_super_admin_can_access_any(self):
        """super_admin can manage any scope."""
        assert _check_announcement_scope_access(["super_admin"], "system")
        assert _check_announcement_scope_access(["super_admin"], "tenant")
        assert _check_announcement_scope_access(["super_admin"], "dept")

    def test_tenant_admin_can_access_tenant_dept(self):
        """tenant_admin can manage tenant and dept scopes, not system."""
        assert _check_announcement_scope_access(["tenant_admin"], "tenant")
        assert _check_announcement_scope_access(["tenant_admin"], "dept")
        assert not _check_announcement_scope_access(["tenant_admin"], "system")

    def test_dept_admin_can_access_own_dept_only(self):
        """dept_admin can only manage their own department's announcements."""
        assert _check_announcement_scope_access(["dept_admin"], "dept", DEPT_ID_A, DEPT_ID_A)
        assert not _check_announcement_scope_access(["dept_admin"], "dept", DEPT_ID_A, DEPT_ID_B)
        assert not _check_announcement_scope_access(["dept_admin"], "tenant", DEPT_ID_A, None)
        assert not _check_announcement_scope_access(["dept_admin"], "system")

    def test_dept_editor_can_access_own_dept_only(self):
        """dept_editor follows same rule as dept_admin."""
        assert _check_announcement_scope_access(["dept_editor"], "dept", DEPT_ID_A, DEPT_ID_A)
        assert not _check_announcement_scope_access(["dept_editor"], "dept", DEPT_ID_A, DEPT_ID_B)
        assert not _check_announcement_scope_access(["dept_editor"], "system")

    def test_empty_roles_cannot_manage(self):
        """Empty role list → no access."""
        assert not _check_announcement_scope_access([], "system")
        assert not _check_announcement_scope_access([], "tenant")
        assert not _check_announcement_scope_access([], "dept")
