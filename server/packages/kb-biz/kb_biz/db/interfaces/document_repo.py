import uuid
from abc import ABC, abstractmethod
from typing import Optional

from kb_biz.models.document import Document


class DocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: uuid.UUID) -> Optional[Document]: ...
    @abstractmethod
    async def list_by_dept(self, dept_id: uuid.UUID) -> list[Document]: ...
    @abstractmethod
    async def create(self, document: Document) -> Document: ...
    @abstractmethod
    async def update(self, document: Document) -> Document: ...
    @abstractmethod
    async def delete(self, id: uuid.UUID) -> None: ...
