from enum import Enum


class RequirementType(Enum):
    MUST = "MUST"
    SHOULD = "SHOULD"
    MAY = "MAY"

    def is_mandatory(self) -> bool:
        return self == RequirementType.MUST

    def is_optional(self) -> bool:
        return self == RequirementType.MAY

    @classmethod
    def from_string(cls, value: str) -> "RequirementType":
        return cls(value.upper())
