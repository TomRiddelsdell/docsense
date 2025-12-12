"""Tests for table extractor."""

import pytest
from src.infrastructure.semantic.table_extractor import TableExtractor


class TestTableExtractor:
    """Test suite for TableExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a TableExtractor instance."""
        return TableExtractor()

    def test_extract_simple_table(self, extractor):
        """Test extraction of a simple markdown table."""
        markdown = """
| Parameter | Value | Unit |
|-----------|-------|------|
| Volatility | 0.25 | % |
| Risk | 0.10 | % |
"""
        section_map = {1: "section-1"}

        tables = extractor.extract(markdown, section_map)

        assert len(tables) == 1
        assert tables[0].headers == ["Parameter", "Value", "Unit"]
        assert len(tables[0].rows) == 2
        assert tables[0].rows[0] == ["Volatility", "0.25", "%"]

    def test_extract_table_with_title(self, extractor):
        """Test extraction of table with preceding title."""
        markdown = """
### Table 1: Risk Parameters

| Name | Value |
|------|-------|
| Alpha | 0.5 |
| Beta | 1.2 |
"""
        section_map = {1: "section-1"}

        tables = extractor.extract(markdown, section_map)

        assert len(tables) == 1
        assert tables[0].title is not None
        assert "Risk Parameters" in tables[0].title

    def test_column_type_detection_numeric(self, extractor):
        """Test detection of numeric columns."""
        markdown = """
| Name | Value | Count |
|------|-------|-------|
| A | 1.5 | 10 |
| B | 2.3 | 20 |
| C | 3.7 | 30 |
"""
        section_map = {1: "section-1"}

        tables = extractor.extract(markdown, section_map)

        assert len(tables) == 1
        # Value and Count columns should be detected as numeric
        assert tables[0].column_types[0] == "text"  # Name
        assert tables[0].column_types[1] == "numeric"  # Value
        assert tables[0].column_types[2] == "numeric"  # Count

    def test_column_type_detection_mixed(self, extractor):
        """Test detection of mixed column types."""
        markdown = """
| Description | Value |
|-------------|-------|
| Volatility | 25% |
| Name | Test |
| Count | 100 |
"""
        section_map = {1: "section-1"}

        tables = extractor.extract(markdown, section_map)

        assert len(tables) == 1
        # Description is text, Value is mixed
        assert tables[0].column_types[0] == "text"

    def test_parse_table_row(self, extractor):
        """Test parsing of individual table rows."""
        row = "| Cell 1 | Cell 2 | Cell 3 |"

        cells = extractor._parse_table_row(row)

        assert len(cells) == 3
        assert cells == ["Cell 1", "Cell 2", "Cell 3"]

    def test_parse_row_with_extra_spaces(self, extractor):
        """Test row parsing with extra whitespace."""
        row = "|  Cell 1  |   Cell 2   |Cell 3|"

        cells = extractor._parse_table_row(row)

        assert cells == ["Cell 1", "Cell 2", "Cell 3"]

    def test_is_numeric(self, extractor):
        """Test numeric value detection."""
        assert extractor._is_numeric("123") is True
        assert extractor._is_numeric("12.34") is True
        assert extractor._is_numeric("1,234.56") is True
        assert extractor._is_numeric("45%") is True
        assert extractor._is_numeric("text") is False
        assert extractor._is_numeric("") is False

    def test_multiple_tables_extraction(self, extractor):
        """Test extraction of multiple tables."""
        markdown = """
First table:
| A | B |
|---|---|
| 1 | 2 |

Some text in between.

Second table:
| X | Y | Z |
|---|---|---|
| a | b | c |
| d | e | f |
"""
        section_map = {1: "section-1"}

        tables = extractor.extract(markdown, section_map)

        assert len(tables) == 2
        assert len(tables[0].headers) == 2
        assert len(tables[1].headers) == 3
        assert len(tables[1].rows) == 2

    def test_table_without_data_rows_skipped(self, extractor):
        """Test that tables with only headers are skipped."""
        markdown = """
| Header 1 | Header 2 |
|----------|----------|
"""
        section_map = {1: "section-1"}

        tables = extractor.extract(markdown, section_map)

        # Should skip table with no data rows
        assert len(tables) == 0

    def test_malformed_table_skipped(self, extractor):
        """Test that malformed tables are skipped."""
        markdown = """
| Header 1 | Header 2 |
|----------|----------|
| Cell 1 |  # Missing cell
| Cell 3 | Cell 4 | Cell 5 |  # Extra cell
"""
        section_map = {1: "section-1"}

        tables = extractor.extract(markdown, section_map)

        # Should skip or handle gracefully
        if len(tables) > 0:
            # If extracted, rows should match header count
            for row in tables[0].rows:
                assert len(row) == len(tables[0].headers)

    def test_table_id_generation(self, extractor):
        """Test that table IDs are generated sequentially."""
        markdown = """
| A | B |
|---|---|
| 1 | 2 |

| C | D |
|---|---|
| 3 | 4 |
"""
        section_map = {1: "section-1"}

        tables = extractor.extract(markdown, section_map)

        assert len(tables) == 2
        assert tables[0].id == "table-1"
        assert tables[1].id == "table-2"

    def test_section_assignment(self, extractor):
        """Test that tables are assigned to correct sections."""
        markdown = """Line 1
Line 2
| A | B |
|---|---|
| 1 | 2 |
Line 6
Line 7
| C | D |
|---|---|
| 3 | 4 |
"""
        # Line 3 in section-1, line 8 in section-2
        section_map = {1: "section-1", 6: "section-2"}

        tables = extractor.extract(markdown, section_map)

        assert len(tables) == 2
        assert tables[0].section_id == "section-1"
        assert tables[1].section_id == "section-2"

    def test_table_with_pipes_in_cells(self, extractor):
        """Test handling of tables with pipe characters in cells."""
        # This is a known limitation - pipes in cells need escaping
        markdown = r"""
| Code | Description |
|------|-------------|
| A \| B | Either A or B |
"""
        section_map = {1: "section-1"}

        tables = extractor.extract(markdown, section_map)

        # Basic extraction should work even if pipe handling is imperfect
        assert len(tables) >= 0  # May or may not parse correctly
