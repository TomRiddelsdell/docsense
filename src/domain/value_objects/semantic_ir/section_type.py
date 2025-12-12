"""Section type classification for semantic IR."""

from enum import Enum


class SectionType(Enum):
    """Semantic classification of document sections."""

    NARRATIVE = "narrative"
    DEFINITION = "definition"
    FORMULA = "formula"
    TABLE = "table"
    CODE = "code"
    GLOSSARY = "glossary"
    ANNEX = "annex"
    UNKNOWN = "unknown"

    def __str__(self) -> str:
        return self.value
