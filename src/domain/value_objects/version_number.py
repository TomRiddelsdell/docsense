from dataclasses import dataclass
from functools import total_ordering


@total_ordering
@dataclass(frozen=True)
class VersionNumber:
    major: int = 1
    minor: int = 0
    patch: int = 0

    def __post_init__(self):
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError("Version components must be non-negative")

    @classmethod
    def from_string(cls, value: str) -> "VersionNumber":
        try:
            parts = value.split(".")
            if len(parts) != 3:
                raise ValueError(f"Invalid version format: {value}")
            return cls(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid version format: {value}") from e

    def increment_patch(self) -> "VersionNumber":
        return VersionNumber(self.major, self.minor, self.patch + 1)

    def increment_minor(self) -> "VersionNumber":
        return VersionNumber(self.major, self.minor + 1, 0)

    def increment_major(self) -> "VersionNumber":
        return VersionNumber(self.major + 1, 0, 0)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    def __lt__(self, other: "VersionNumber") -> bool:
        if not isinstance(other, VersionNumber):
            return NotImplemented
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VersionNumber):
            return NotImplemented
        return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
