"""Table extraction from markdown content."""

import re
import uuid
from typing import List, Optional

from src.domain.value_objects.semantic_ir import TableData


class TableExtractor:
    """Extract tables from markdown content."""

    def extract(self, markdown: str, section_id_map: dict) -> List[TableData]:
        """
        Extract tables from markdown content.

        Args:
            markdown: Markdown content
            section_id_map: Map from line numbers to section IDs

        Returns:
            List of TableData objects
        """
        tables = []
        table_counter = 1

        lines = markdown.split('\n')
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this line looks like a markdown table row
            if '|' in line and line.strip().startswith('|'):
                # Extract the complete table
                table_lines = []
                title = self._find_table_title(lines, i)

                # Collect all consecutive table rows
                j = i
                while j < len(lines) and '|' in lines[j]:
                    table_lines.append(lines[j].strip())
                    j += 1

                if len(table_lines) >= 2:  # At least header + separator
                    table = self._parse_table(
                        table_lines, f"table-{table_counter}", title, i + 1, section_id_map
                    )
                    if table:
                        tables.append(table)
                        table_counter += 1

                i = j
            else:
                i += 1

        return tables

    def _find_table_title(self, lines: List[str], table_start: int) -> Optional[str]:
        """
        Find table title by looking at preceding lines.

        Args:
            lines: All document lines
            table_start: Index where table starts

        Returns:
            Table title or None
        """
        # Look at the previous 3 lines for a heading
        for i in range(max(0, table_start - 3), table_start):
            line = lines[i].strip()
            if line.startswith('#'):
                # Extract heading text
                return line.lstrip('#').strip()
            if line and len(line) < 100 and ':' in line:
                # Might be a title like "Table 1: Parameters"
                return line

        return None

    def _parse_table(
        self,
        table_lines: List[str],
        table_id: str,
        title: Optional[str],
        line_number: int,
        section_id_map: dict,
    ) -> Optional[TableData]:
        """
        Parse markdown table lines into TableData.

        Args:
            table_lines: Lines of the markdown table
            table_id: ID for the table
            title: Table title if found
            line_number: Line number of table
            section_id_map: Map to find section ID

        Returns:
            TableData object or None if parsing failed
        """
        if len(table_lines) < 2:
            return None

        # Find section ID
        section_id = self._find_section_for_line(line_number, section_id_map)
        if not section_id:
            section_id = "section-unknown"

        # Parse header row
        headers = self._parse_table_row(table_lines[0])
        if not headers:
            return None

        # Skip separator row (index 1)
        # Parse data rows
        rows = []
        for line in table_lines[2:]:
            row = self._parse_table_row(line)
            if row and len(row) == len(headers):
                rows.append(row)

        if not rows:
            return None

        # Detect column types
        column_types = self._detect_column_types(rows, len(headers))

        return TableData(
            id=table_id,
            title=title,
            headers=headers,
            rows=rows,
            column_types=column_types,
            section_id=section_id,
        )

    def _parse_table_row(self, line: str) -> List[str]:
        """
        Parse a single markdown table row.

        Args:
            line: Table row line

        Returns:
            List of cell values
        """
        # Remove leading/trailing pipes and split
        line = line.strip()
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]

        cells = [cell.strip() for cell in line.split('|')]
        return cells

    def _detect_column_types(self, rows: List[List[str]], column_count: int) -> List[str]:
        """
        Detect the type of each column.

        Args:
            rows: Table rows
            column_count: Number of columns

        Returns:
            List of column types
        """
        column_types = []

        for col_idx in range(column_count):
            column_values = [row[col_idx] for row in rows if col_idx < len(row)]

            # Check if all values are numeric
            numeric_count = sum(1 for v in column_values if self._is_numeric(v))
            if numeric_count / len(column_values) > 0.8:
                column_types.append("numeric")
            else:
                column_types.append("text")

        return column_types

    def _is_numeric(self, value: str) -> bool:
        """Check if a value is numeric."""
        value = value.strip().replace(',', '').replace('%', '')
        try:
            float(value)
            return True
        except ValueError:
            return False

    def _find_section_for_line(self, line_number: int, section_id_map: dict) -> Optional[str]:
        """Find section ID for a line number."""
        for start_line, section_id in sorted(section_id_map.items(), reverse=True):
            if line_number >= start_line:
                return section_id
        return None
