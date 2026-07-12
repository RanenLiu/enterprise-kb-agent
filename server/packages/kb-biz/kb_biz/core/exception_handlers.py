from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from kb_biz.core.exceptions import AppException

# Chinese translations for common validation errors
_VALIDATION_ERROR_CN: dict[str, str] = {
    "string_too_short": "最少需要 {min_length} 个字符",
    "string_too_long": "最多允许 {max_length} 个字符",
    "missing": "该字段为必填项",
    "int_parsing": "请输入有效的整数",
    "float_parsing": "请输入有效的数字",
    "greater_than": "值必须大于 {gt}",
    "greater_than_equal": "值必须大于或等于 {ge}",
    "less_than": "值必须小于 {lt}",
    "less_than_equal": "值必须小于或等于 {le}",
    "url_parsing": "URL 格式不正确",
    "email": "邮箱格式不正确",
    "string_pattern_mismatch": "格式不正确",
    "json_invalid": "JSON 格式无效",
    "enum": "请选择有效的选项",
}


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    messages: list[str] = []
    for error in errors:
        field = (
            ".".join(str(loc) for loc in error["loc"][1:])
            if len(error["loc"]) > 1
            else (str(error["loc"][0]) if error["loc"] else "")
        )
        error_type = error["type"]
        ctx = error.get("ctx") or {}
        template = _VALIDATION_ERROR_CN.get(error_type)
        if template:
            # Safely substitute only keys that exist in ctx
            msg = template.format(**{k: v for k, v in ctx.items() if isinstance(v, (str, int, float))})
        else:
            msg = error["msg"]
        messages.append(f"{field}: {msg}" if field else msg)

    logger = request.app.state.logger
    logger.warning("Validation error: %s", messages)

    return JSONResponse(
        status_code=422,
        content={"code": 4000, "message": "; ".join(messages), "data": None},
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "data": None,
            },
        )

    # Unhandled: log full trace
    logger = request.app.state.logger
    logger.exception("Unhandled exception: %s", exc)

    return JSONResponse(
        status_code=500,
        content={
            "code": 5000,
            "message": "Internal server error",
            "data": None,
        },
    )
