from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: str
    dept_id: str
    title: str
    file_name: str
    file_type: str
    file_size: int
    md5: Optional[str] = None
    visibility: str = "dept"
    status: str
    error_message: Optional[str] = None
    file_path: str = ""
    chunk_count: int = 0
    project_id: Optional[str] = None
    uploaded_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UploadResponse(BaseModel):
    id: str
    file_name: str
    file_type: str
    file_size: int
    status: str


class ReindexResponse(BaseModel):
    id: str
    status: str


class VisibilityUpdate(BaseModel):
    visibility: str
