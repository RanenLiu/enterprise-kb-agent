"""LangGraph Agent 工具定义。

工具通过 @tool 装饰器注册，会自动生成 JSON Schema 供 LLM 调用。
"""

from __future__ import annotations

import inspect
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger("kb_biz.chat.tools")

# ── 工具注册表 ────────────────────────────────────────────

_tool_registry: dict[str, dict[str, Any]] = {}


def tool(
    name: str | None = None,
    description: str | None = None,
) -> Callable:
    """装饰器：将异步函数注册为 LLM 可调用的工具。

    从函数签名和文档字符串自动生成 JSON Schema。
    参数名为 dept_ids 的会被自动注入，无需 LLM 填写。
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        sig = inspect.signature(func)
        doc = (description or func.__doc__ or "").strip()

        properties: dict[str, Any] = {}
        required: list[str] = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "dept_ids"):
                continue

            # 根据类型注解映射 JSON Schema 类型
            type_map = {str: "string", int: "integer", float: "number", bool: "boolean"}
            json_type = type_map.get(param.annotation, "string")

            prop: dict[str, Any] = {"type": json_type}

            # 从 docstring 的参数行提取描述
            param_doc = ""
            for line in doc.split("\n"):
                line = line.strip()
                if line.startswith(f"{param_name}:"):
                    param_doc = line.split(":", 1)[1].strip()
            if param_doc:
                prop["description"] = param_doc

            # 处理默认值：有默认值的参数非必需，否则必需
            if param.default is not inspect.Parameter.empty:
                if param.default is not None:
                    prop["default"] = param.default
            else:
                required.append(param_name)

            # 从 docstring 提取枚举约束
            if "(enum:" in doc:
                for line in doc.split("\n"):
                    if f"{param_name}(enum:" in line or f"{param_name} enum:" in line:
                        import re
                        m = re.search(r"enum:\s*\[([^\]]+)\]", line)
                        if m:
                            prop["enum"] = [v.strip() for v in m.group(1).split(",")]

            properties[param_name] = prop

        _tool_registry[tool_name] = {
            "name": tool_name,
            "description": doc.split("\n")[0] if doc else "",
            "fn": func,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def get_tool_definitions() -> list[dict[str, Any]]:
    """返回所有工具的 Schema（不含 fn 字段），供 LLM 工具选择时使用。"""
    return [
        {
            "name": v["name"],
            "description": v["description"],
            "parameters": v["parameters"],
        }
        for v in _tool_registry.values()
    ]


async def execute_tool(
    name: str,
    args: dict[str, Any],
    dept_ids: list[str],
    user_id: str | None = None,
) -> dict[str, Any]:
    """按名称执行已注册的工具。"""
    entry = _tool_registry.get(name)
    if not entry:
        return {"error": f"Unknown tool: {name}"}

    try:
        sig = inspect.signature(entry["fn"])
        kwargs = dict(args)
        if "dept_ids" in sig.parameters:
            kwargs["dept_ids"] = dept_ids
        if "user_id" in sig.parameters:
            kwargs["user_id"] = user_id
        result = await entry["fn"](**kwargs)
        return result if isinstance(result, dict) else {"result": result}
    except Exception as e:
        logger.exception("Tool %s execution failed", name)
        return {"error": str(e)}


# ── 工具实现 ─────────────────────────────────────────────


@tool(description="获取当前日期和时间。用于'最近''上周''现在几点'等时间查询。")
async def get_current_time(timezone: str = "+08:00") -> dict[str, Any]:
    """获取当前时间。

    返回 UTC 时间和指定时区的本地时间。
    timezone: 时区偏移，如 +08:00（中国标准时间），默认 +08:00
    """
    from datetime import timezone as tz_mod
    utc_now = datetime.now(tz_mod.utc)
    try:
        sign = 1 if timezone.startswith("+") else -1
        parts = timezone[1:].split(":")
        hours, mins = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
        local_now = utc_now + timedelta(hours=sign * hours, minutes=sign * mins)
        local_str = local_now.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        local_str = utc_now.strftime("%Y-%m-%d %H:%M:%S")
        timezone = "+00:00"

    return {
        "utc_time": utc_now.strftime("%Y-%m-%d %H:%M:%S"),
        "local_time": local_str,
        "timezone": timezone,
    }


@tool(description="搜索文档内容、阅读文档、回答业务问题。每次用户问文档内容、介绍文档、总结文档时都应该调用此工具。")
async def retrieve_knowledge(
    query: str,
    top_k: int = 15,
    dept_ids: list[str] | None = None,
    user_id: str | None = None,
    doc_ids: list[str] | None = None,
) -> dict[str, Any]:
    """检索知识库。

    三路并行（向量+全文+图谱）→ RRF 融合 → Cross-Encoder 精排。
    可以搜索文档内容来回答关于文档的问题。
    query: 检索关键词，用文档标题或问题原文
    top_k: 返回结果数，默认 15
    dept_ids: 自动注入，无需填写
    user_id: 自动注入，无需填写
    doc_ids: 可选，限定检索的文档 ID 列表
    """
    from kb_biz.services.instances import retrieval_service

    if not query.strip():
        return {"results": [], "message": "查询为空"}

    if retrieval_service is None:
        return {"results": [], "message": "检索服务未初始化"}

    results = await retrieval_service.hybrid_search(
        query, dept_ids or [],
        top_k=int(top_k) if top_k else 8,
        user_id=user_id,
        doc_ids=doc_ids,
    )
    # results returned as list[dict] from search()
    return {
        "results": [
            {
                "chunk_id": r.get("chunk_id", ""),
                "doc_id": r.get("doc_id", ""),
                "dept_id": r.get("dept_id", ""),
                "content": r.get("content", ""),
                "heading_path": r.get("heading_path", ""),
                "page_range": r.get("page_range", ""),
                "score": r.get("score", 0.0),
                "source": r.get("source", ""),
            }
            for r in results
        ],
        "result_count": len(results),
    }


@tool(
    description="查询文档名和元数据（不包含具体内容）。查具体内容必须用retrieve_knowledge。"
    "当用户问'最近上传了什么文档''有哪些PDF文档'时调用此工具",
)
async def query_documents(
    keyword: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    limit: int = 10,
) -> dict[str, Any]:
    """查询文档元数据。

    根据条件过滤 documents 表，返回匹配的文档列表。
    keyword: 文件名关键词搜索
    date_from: 起始日期，ISO格式如 2026-06-01
    date_to: 结束日期，ISO格式如 2026-06-26
    status: 文档状态，枚举值: pending/parsing/chunking/indexing/ready/failed
    sort_by: 排序字段，created_at/updated_at/file_name
    sort_order: asc 或 desc，默认 desc
    limit: 返回条数，默认 10，最大 50
    """
    from sqlalchemy import text as sa_text

    from kb_adapter_postgres.session import async_session_factory

    conditions: list[str] = ["1=1"]
    params: dict[str, Any] = {}

    if keyword:
        import jieba  # noqa: F811
        terms = [t for t in jieba.cut(keyword) if len(t) >= 2]
        if not terms:
            terms = [keyword]
        kw_conditions = []
        for i, term in enumerate(terms):
            kw_conditions.append(f"(file_name ILIKE :kw{i} OR title ILIKE :kw{i})")
            params[f"kw{i}"] = f"%{term}%"
        conditions.append("(" + " OR ".join(kw_conditions) + ")")
    if date_from:
        conditions.append("created_at >= :date_from")
        params["date_from"] = date_from
    if date_to:
        conditions.append("created_at <= :date_to")
        params["date_to"] = f"{date_to}T23:59:59"
    if status:
        allowed_statuses = {"pending", "parsing", "chunking", "indexing", "ready", "failed"}
        if status in allowed_statuses:
            conditions.append("status = :status")
            params["status"] = status


    allowed_sort = {"created_at", "updated_at", "file_name"}
    if sort_by not in allowed_sort:
        sort_by = "created_at"
    sort_dir = "DESC" if sort_order and sort_order.lower() == "desc" else "ASC"
    limit = min(max(int(limit) if limit else 10, 1), 50)

    sql = sa_text(
        f"SELECT id, file_name, status, created_at, updated_at, dept_id, chunk_count, visibility "
        f"FROM documents WHERE {' AND '.join(conditions)} "
        f"ORDER BY {sort_by} {sort_dir} LIMIT :limit"
    )
    params["limit"] = limit

    async with async_session_factory() as session:
        try:
            rows = await session.execute(sql, params)
            return {
                "documents": [
                    {
                        "id": str(r.id),
                        "file_name": r.file_name,
                        "status": r.status,
                        "created_at": str(r.created_at) if r.created_at else None,
                        "updated_at": str(r.updated_at) if r.updated_at else None,
                        "dept_id": str(r.dept_id) if r.dept_id else None,
                        "chunk_count": r.chunk_count,
                        "visibility": r.visibility,
                        "project_id": str(r.project_id) if hasattr(r, 'project_id') and r.project_id else None,
                    }
                    for r in rows
                ],
                "total": rows.rowcount if hasattr(rows, "rowcount") else 0,
            }
        except Exception as e:
            logger.exception("Query documents failed")
            return {"error": str(e)}
