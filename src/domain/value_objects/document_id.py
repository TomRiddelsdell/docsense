from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DocumentId:
    value: UUID

    @classmethod
    def generate(cls) -> "DocumentId":
        return cls(uuid4())

    @classmethod
    def from_string(cls, value: str) -> "DocumentId":
        return cls(UUID(value))

    def __str__(self) -> str:
        return str(self.value)
