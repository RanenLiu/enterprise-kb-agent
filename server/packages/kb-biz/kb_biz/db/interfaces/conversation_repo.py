import uuid
from abc import ABC, abstractmethod
from typing import Optional

from kb_biz.models.conversation import ConversationSession, ConversationMessage


class ConversationRepository(ABC):
    @abstractmethod
    async def get_session_by_id(self, id: uuid.UUID) -> Optional[ConversationSession]: ...
    @abstractmethod
    async def list_sessions_by_user(self, user_id: uuid.UUID) -> list[ConversationSession]: ...
    @abstractmethod
    async def create_session(self, session: ConversationSession) -> ConversationSession: ...
    @abstractmethod
    async def update_session(self, session: ConversationSession) -> ConversationSession: ...
    @abstractmethod
    async def delete_session(self, id: uuid.UUID) -> None: ...
