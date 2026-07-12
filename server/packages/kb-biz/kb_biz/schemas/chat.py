from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SessionResponse(BaseModel):
    id: str
    title: str
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime


class SessionCreateResponse(BaseModel):
    id: str
    title: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    metadata: Optional[dict] = None
    created_at: datetime


class ChatRequest(BaseModel):
    session_id: str = ""  # empty string creates a new session
    content: str
    deep_thinking: bool = False
    timezone: str = "+08:00"  # User timezone, auto-detected by frontend

    @classmethod
    def get_example(cls) -> dict:
        return {"session_id": "uuid-or-empty", "content": "What is the reimbursement process?"}
