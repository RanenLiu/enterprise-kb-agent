"""Tests for seed menu structure: verify announcement menu item exists with correct attributes."""

from __future__ import annotations

import ast
from pathlib import Path

SEED_DIR = Path(__file__).parents[3] / "scripts"


def _find_sys_children_menus(seed_file: str) -> list[dict]:
    """Parse a seed script and extract Menu() calls added to sys_children list.

    Returns list of dicts with name, path, icon, permission_code, sort_order.
    """
    tree = ast.parse((SEED_DIR / seed_file).read_text())

    # Find the sys_children list being extended with .append or defined as a list
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "sys_children":
                    if isinstance(node.value, ast.List):
                        return [_parse_menu_call(el) for el in node.value.elts if isinstance(el, ast.Call)]

    # Also search for sys_children being used with session.add_all
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "add_all":
                for arg in node.args:
                    if isinstance(arg, ast.List):
                        items = []
                        for el in arg.elts:
                            if isinstance(el, ast.Call) and _is_menu_call(el):
                                items.append(_parse_menu_call(el))
                            elif isinstance(el, ast.Name) and el.id == "sys_children":
                                # sys_children variable referenced, skip
                                pass
                        if items:
                            return items

    return []


def _is_menu_call(node: ast.Call) -> bool:
    return isinstance(node.func, ast.Name) and node.func.id == "Menu"


def _parse_menu_call(node: ast.Call) -> dict:
    """Extract keyword arguments from a Menu(...) call."""
    menu: dict = {"name": "", "path": None, "icon": None, "permission_code": None, "sort_order": 0, "parent_id": None}
    for kw in node.keywords:
        if isinstance(kw.value, ast.Constant):
            menu[kw.arg] = kw.value.value
        elif isinstance(kw.value, ast.Name) and kw.value.id == "sys_mgmt":
            menu["parent_id"] = "sys_mgmt"
        elif kw.arg == "parent_id":
            # Non-constant parent_id, try to resolve
            if isinstance(kw.value, ast.Attribute):
                menu["parent_id"] = ast.unparse(kw.value)
    return menu


def _extract_sys_children_menus_from_all_menus(seed_file: str) -> list[dict]:
    """More robust: extract all Menu calls and filter those with parent_id=sys_mgmt.id."""
    tree = ast.parse((SEED_DIR / seed_file).read_text())
    menus: list[dict] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "sys_children":
                    if isinstance(node.value, ast.List):
                        for el in node.value.elts:
                            if isinstance(el, ast.Call) and _is_menu_call(el):
                                menus.append(_parse_menu_call(el))

    return menus


class TestSeedMenusOS:
    """Verify open source seed script has correct announcement menu item."""

    def test_announcement_menu_exists(self):
        menus = _extract_sys_children_menus_from_all_menus("seed_os.py")
        ann = [m for m in menus if m.get("name") == "系统公告"]
        assert len(ann) == 1, "Should have exactly one '系统公告' menu item"

    def test_announcement_menu_attributes(self):
        menus = _extract_sys_children_menus_from_all_menus("seed_os.py")
        ann = [m for m in menus if m.get("name") == "系统公告"][0]
        assert ann["path"] == "/admin/announcements"
        assert ann["icon"] == "Megaphone"
        assert ann["permission_code"] is None  # RBAC via role-menu assignment only
        assert ann["parent_id"] == "sys_mgmt.id"

    def test_announcement_menu_sort_order(self):
        menus = _extract_sys_children_menus_from_all_menus("seed_os.py")
        ann = [m for m in menus if m.get("name") == "系统公告"][0]
        assert ann["sort_order"] == 4  # After 模型配置(3), before 系统设置(5)


class TestSeedMenusEnterprise:
    """Verify enterprise seed script has correct announcement menu item."""

    def test_announcement_menu_exists(self):
        menus = _extract_sys_children_menus_from_all_menus("seed_enterprise.py")
        ann = [m for m in menus if m.get("name") == "系统公告"]
        assert len(ann) == 1, "Should have exactly one '系统公告' menu item"

    def test_announcement_menu_attributes(self):
        menus = _extract_sys_children_menus_from_all_menus("seed_enterprise.py")
        ann = [m for m in menus if m.get("name") == "系统公告"][0]
        assert ann["path"] == "/admin/announcements"
        assert ann["icon"] == "Megaphone"
        assert ann["permission_code"] is None
        assert ann["parent_id"] == "sys_mgmt.id"

    def test_announcement_menu_sort_order(self):
        menus = _extract_sys_children_menus_from_all_menus("seed_enterprise.py")
        ann = [m for m in menus if m.get("name") == "系统公告"][0]
        assert ann["sort_order"] == 5  # After 菜单管理(4), before 系统监控(6)
