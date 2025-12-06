from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Section:
    heading: str
    content: str
    level: int
    subsections: List["Section"] = field(default_factory=list)

    def __post_init__(self):
        if self.level < 1 or self.level > 6:
            raise ValueError(f"Section level must be between 1 and 6, got {self.level}")

    def word_count(self) -> int:
        return len(self.content.split())

    def is_empty(self) -> bool:
        return len(self.content.strip()) == 0
