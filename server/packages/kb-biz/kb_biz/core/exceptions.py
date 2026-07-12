from __future__ import annotations

from fastapi import HTTPException


class AppException(HTTPException):
    def __init__(self, code: int, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(status_code=status_code, detail=message)


class NotFoundException(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(code=4004, message=f"{resource} not found", status_code=404)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(code=4001, message=message, status_code=401)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(code=4003, message=message, status_code=403)


class ConflictException(AppException):
    def __init__(self, message: str = "Conflict"):
        super().__init__(code=4009, message=message, status_code=409)


class ValidationException(AppException):
    def __init__(self, message: str = "Validation error"):
        super().__init__(code=4220, message=message, status_code=422)
