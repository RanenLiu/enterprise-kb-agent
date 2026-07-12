import uuid
from abc import ABC, abstractmethod
from typing import Optional

from kb_biz.models.department import Department


class DepartmentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: uuid.UUID) -> Optional[Department]: ...
    @abstractmethod
    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[Department]: ...
    @abstractmethod
    async def create(self, dept: Department) -> Department: ...
    @abstractmethod
    async def update(self, dept: Department) -> Department: ...
    @abstractmethod
    async def delete(self, id: uuid.UUID) -> None: ...
