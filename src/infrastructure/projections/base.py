from abc import ABC, abstractmethod
from typing import List, Type

from src.domain.events import DomainEvent


class Projection(ABC):
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        pass

    @abstractmethod
    def handles(self) -> List[Type[DomainEvent]]:
        pass

    def can_handle(self, event: DomainEvent) -> bool:
        return type(event) in self.handles()
