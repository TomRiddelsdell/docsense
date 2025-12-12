"""Table data value object for semantic IR."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass(frozen=True)
class TableData:
    """Structured table representation."""

    id: str
    headers: List[str]
    rows: List[List[str]]
    section_id: str
    title: Optional[str] = None
    column_types: List[str] = field(default_factory=list)  # "text", "numeric", "formula", "mixed"

    def __post_init__(self) -> None:
        """Validate table data."""
        if not self.id:
            raise ValueError("Table ID cannot be empty")
        if not self.section_id:
            raise ValueError("Section ID cannot be empty")
        if not self.headers:
            raise ValueError("Table must have at least one header")

        # Validate that all rows have the same number of columns as headers
        header_count = len(self.headers)
        for idx, row in enumerate(self.rows):
            if len(row) != header_count:
                raise ValueError(
                    f"Row {idx} has {len(row)} columns, expected {header_count}"
                )

        # Validate column types if provided
        if self.column_types and len(self.column_types) != header_count:
            raise ValueError(
                f"Column types count ({len(self.column_types)}) must match "
                f"headers count ({header_count})"
            )

    @property
    def row_count(self) -> int:
        """Get the number of rows in the table."""
        return len(self.rows)

    @property
    def column_count(self) -> int:
        """Get the number of columns in the table."""
        return len(self.headers)

    def get_cell(self, row: int, column: int) -> str:
        """
        Get the cell value at the specified row and column.

        Args:
            row: Row index (0-based)
            column: Column index (0-based)

        Returns:
            Cell value as string

        Raises:
            IndexError: If row or column is out of bounds
        """
        if row < 0 or row >= len(self.rows):
            raise IndexError(f"Row index {row} out of range [0, {len(self.rows)})")
        if column < 0 or column >= len(self.headers):
            raise IndexError(f"Column index {column} out of range [0, {len(self.headers)})")
        return self.rows[row][column]

    def get_column(self, column: int) -> List[str]:
        """Get all values in the specified column."""
        if column < 0 or column >= len(self.headers):
            raise IndexError(f"Column index {column} out of range [0, {len(self.headers)})")
        return [row[column] for row in self.rows]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TableData":
        """
        Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            TableData instance
        """
        return cls(
            id=data["id"],
            headers=data["headers"],
            rows=data["rows"],
            section_id=data["section_id"],
            title=data.get("title"),
            column_types=data.get("column_types", []),
        )
