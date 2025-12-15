"""End-to-end tests for Semantic Intermediate Representation (IR) extraction.

This test suite validates that the document conversion pipeline correctly
extracts semantic content (formulas, definitions, tables, cross-references)
from Word documents and builds the expected IR structure per ADR-014.
"""
import json
import pytest
import pytest_asyncio
from pathlib import Path
from typing import Dict, List, Any


TEST_DOCS_DIR = Path("/workspaces/data/test_documents")


def get_documents_with_semantic_ir() -> List[Dict[str, Any]]:
    """Load test documents that have expected semantic IR data."""
    test_docs = []

    docx_files = sorted(TEST_DOCS_DIR.glob("*.docx"))

    for docx_file in docx_files:
        json_file = docx_file.with_suffix(".json")

        if not json_file.exists():
            continue

        with open(json_file, "r") as f:
            expected = json.load(f)

        # Only include documents that have semantic IR expectations
        if "expected_semantic_ir" not in expected:
            continue

        semantic_ir = expected["expected_semantic_ir"]

        # Skip documents with no semantic content
        if (not semantic_ir.get("definitions") and
            not semantic_ir.get("formulae") and
            not semantic_ir.get("tables") and
            not semantic_ir.get("cross_references")):
            continue

        test_docs.append({
            "docx_path": docx_file,
            "document_id": expected["document_id"],
            "title": expected["title"],
            "expected_semantic_ir": semantic_ir,
        })

    return test_docs


# Documents with semantic content for parametrized tests
semantic_test_documents = get_documents_with_semantic_ir()
semantic_test_ids = [doc["document_id"] for doc in semantic_test_documents]


@pytest.fixture
def test_policy_data():
    """Policy repository for tests."""
    return {
        "name": f"Semantic IR Test Policy",
        "description": "Policy for semantic IR testing",
    }


class TestSemanticIRE2E:
    """End-to-end tests for Semantic IR extraction."""

    @pytest_asyncio.fixture
    async def policy_repository(self, authenticated_client, test_policy_data):
        """Create a policy repository for testing."""
        response = await authenticated_client.post(
            "/api/v1/policy-repositories",
            json=test_policy_data,
        )
        assert response.status_code == 201
        return response.json()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_doc", semantic_test_documents, ids=semantic_test_ids)
    async def test_semantic_ir_extraction(self, authenticated_client, policy_repository, test_doc):
        """Test semantic IR extraction for each document with semantic content.

        This test:
        1. Uploads the .docx file
        2. Retrieves the semantic IR via GET /api/v1/documents/{id}/semantic-ir
        3. Validates extracted semantic content against expected IR
        """
        docx_path = test_doc["docx_path"]
        expected_ir = test_doc["expected_semantic_ir"]

        # Upload document
        with open(docx_path, "rb") as f:
            docx_content = f.read()

        upload_response = await authenticated_client.post(
            "/api/v1/documents",
            files={
                "file": (
                    docx_path.name,
                    docx_content,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            },
            data={"title": test_doc["title"]},
        )

        assert upload_response.status_code == 201, (
            f"Failed to upload {docx_path.name}: {upload_response.text}"
        )

        doc_id = upload_response.json()["id"]

        # Get semantic IR
        ir_response = await authenticated_client.get(
            f"/api/v1/documents/{doc_id}/semantic-ir"
        )

        # If endpoint doesn't exist yet, skip validation for now
        if ir_response.status_code == 404:
            pytest.skip("Semantic IR endpoint not yet implemented")

        assert ir_response.status_code == 200, (
            f"Failed to get semantic IR for {docx_path.name}: {ir_response.text}"
        )

        actual_ir = ir_response.json()

        # Validate semantic content
        self._validate_semantic_ir(
            test_doc["document_id"],
            expected_ir,
            actual_ir
        )

    def _validate_semantic_ir(
        self,
        document_id: str,
        expected: Dict[str, Any],
        actual: Dict[str, Any]
    ):
        """Validate extracted semantic IR against expected IR.

        Args:
            document_id: Document identifier for error messages
            expected: Expected semantic IR from JSON file
            actual: Actual semantic IR from API
        """
        # Validate definitions
        if expected.get("definitions"):
            self._validate_definitions(
                document_id,
                expected["definitions"],
                actual.get("definitions", [])
            )

        # Validate formulae
        if expected.get("formulae"):
            self._validate_formulae(
                document_id,
                expected["formulae"],
                actual.get("formulae", [])
            )

        # Validate tables
        if expected.get("tables"):
            self._validate_tables(
                document_id,
                expected["tables"],
                actual.get("tables", [])
            )

        # Validate cross-references
        if expected.get("cross_references"):
            self._validate_cross_references(
                document_id,
                expected["cross_references"],
                actual.get("cross_references", [])
            )

    def _validate_definitions(
        self,
        document_id: str,
        expected: List[Dict],
        actual: List[Dict]
    ):
        """Validate definition extraction."""
        expected_count = len(expected)
        actual_count = len(actual)

        # Allow some variance in definition detection (±1 for low counts, ±2 for high)
        variance = 1 if expected_count <= 3 else 2

        assert abs(actual_count - expected_count) <= variance, (
            f"{document_id}: Expected ~{expected_count} definitions, "
            f"found {actual_count} (allowed variance: ±{variance})"
        )

        # Validate that key terms are extracted
        # At least 70% of expected terms should be found
        if expected:
            expected_terms = {d["term"].lower() for d in expected}
            actual_terms = {d.get("term", "").lower() for d in actual}

            found_terms = expected_terms.intersection(actual_terms)
            match_rate = len(found_terms) / len(expected_terms) if expected_terms else 1

            assert match_rate >= 0.7, (
                f"{document_id}: Term extraction rate too low: {match_rate:.1%} "
                f"(expected ≥70%)"
            )

    def _validate_formulae(
        self,
        document_id: str,
        expected: List[Dict],
        actual: List[Dict]
    ):
        """Validate formula extraction."""
        expected_count = len(expected)
        actual_count = len(actual)

        # Formulas are critical - require higher accuracy
        # Allow ±1 variance
        variance = 1

        assert abs(actual_count - expected_count) <= variance, (
            f"{document_id}: Expected ~{expected_count} formulas, "
            f"found {actual_count} (allowed variance: ±{variance})"
        )

        # Validate that formula names/expressions are extracted
        if expected and actual:
            # Check that at least 80% of expected formulas are found
            expected_exprs = {
                f.get("expression", f.get("name", "")).lower()
                for f in expected
            }
            actual_exprs = {
                f.get("expression", f.get("name", "")).lower()
                for f in actual
            }

            # Fuzzy matching - check if expected expression substring is in actual
            found_count = sum(
                1 for exp_expr in expected_exprs
                if any(exp_expr[:20] in act_expr for act_expr in actual_exprs)
            )

            match_rate = found_count / len(expected_exprs) if expected_exprs else 1

            assert match_rate >= 0.8, (
                f"{document_id}: Formula extraction rate too low: {match_rate:.1%} "
                f"(expected ≥80%)"
            )

    def _validate_tables(
        self,
        document_id: str,
        expected: List[Dict],
        actual: List[Dict]
    ):
        """Validate table extraction."""
        expected_count = len(expected)
        actual_count = len(actual)

        # Tables should be extracted exactly (they're well-structured)
        assert actual_count == expected_count, (
            f"{document_id}: Expected {expected_count} tables, "
            f"found {actual_count}"
        )

        # Validate table structure (headers, row counts)
        for exp_table in expected:
            # Find matching table by row/column count
            matching_tables = [
                t for t in actual
                if (t.get("row_count") == exp_table.get("row_count") and
                    t.get("column_count") == exp_table.get("column_count"))
            ]

            assert len(matching_tables) > 0, (
                f"{document_id}: No table found with "
                f"{exp_table.get('row_count')} rows x {exp_table.get('column_count')} cols"
            )

    def _validate_cross_references(
        self,
        document_id: str,
        expected: List[Dict],
        actual: List[Dict]
    ):
        """Validate cross-reference extraction."""
        expected_count = len(expected)
        actual_count = len(actual)

        # Cross-references can vary (some might be missed or extras found)
        # Allow 50% variance
        variance = max(1, expected_count // 2)

        assert abs(actual_count - expected_count) <= variance, (
            f"{document_id}: Expected ~{expected_count} cross-references, "
            f"found {actual_count} (allowed variance: ±{variance})"
        )

    @pytest.mark.asyncio
    async def test_formula_documents_have_formulae(self, authenticated_client, policy_repository):
        """Test that documents known to contain formulas have formulae in IR."""
        formula_docs = [
            doc for doc in semantic_test_documents
            if doc["document_id"] in ["doc_01_clean", "doc_04_incomplete_formulas", "doc_12_formula_precision"]
        ]

        for test_doc in formula_docs:
            # Upload
            with open(test_doc["docx_path"], "rb") as f:
                docx_content = f.read()

            upload_response = await authenticated_client.post(
                "/api/v1/documents",
                files={
                    "file": (
                        test_doc["docx_path"].name,
                        docx_content,
                        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
                },
                data={"title": test_doc["title"]},
            )

            assert upload_response.status_code == 201
            doc_id = upload_response.json()["id"]

            # Get semantic IR
            ir_response = await authenticated_client.get(
                f"/api/v1/documents/{doc_id}/semantic-ir"
            )

            if ir_response.status_code == 404:
                pytest.skip("Semantic IR endpoint not yet implemented")

            assert ir_response.status_code == 200
            ir_data = ir_response.json()

            # Should have formulae
            formulae = ir_data.get("formulae", [])
            assert len(formulae) > 0, (
                f"{test_doc['document_id']} should have formulas in semantic IR"
            )

    @pytest.mark.asyncio
    async def test_cross_reference_document(self, authenticated_client, policy_repository):
        """Test cross-reference extraction for doc_02 (missing appendix)."""
        test_doc = next(
            (doc for doc in semantic_test_documents
             if doc["document_id"] == "doc_02_missing_appendix"),
            None
        )

        if not test_doc:
            pytest.skip("doc_02_missing_appendix not found")

        # Upload
        with open(test_doc["docx_path"], "rb") as f:
            docx_content = f.read()

        upload_response = await authenticated_client.post(
            "/api/v1/documents",
            files={
                "file": (
                    test_doc["docx_path"].name,
                    docx_content,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            },
            data={"title": test_doc["title"]},
        )

        assert upload_response.status_code == 201
        doc_id = upload_response.json()["id"]

        # Get semantic IR
        ir_response = await authenticated_client.get(
            f"/api/v1/documents/{doc_id}/semantic-ir"
        )

        if ir_response.status_code == 404:
            pytest.skip("Semantic IR endpoint not yet implemented")

        assert ir_response.status_code == 200
        ir_data = ir_response.json()

        # Should have cross-references (this document references missing appendices)
        cross_refs = ir_data.get("cross_references", [])
        assert len(cross_refs) > 0, (
            "doc_02_missing_appendix should have cross-references in semantic IR"
        )

        # Should reference appendices
        appendix_refs = [
            ref for ref in cross_refs
            if "appendix" in ref.get("target", "").lower()
        ]

        assert len(appendix_refs) > 0, (
            "doc_02 should have appendix cross-references"
        )

    @pytest.mark.asyncio
    async def test_semantic_ir_download(self, authenticated_client, policy_repository):
        """Test downloading semantic IR as JSON."""
        # Use doc_04 which has good semantic content
        test_doc = next(
            (doc for doc in semantic_test_documents
             if doc["document_id"] == "doc_04_incomplete_formulas"),
            None
        )

        if not test_doc:
            pytest.skip("doc_04_incomplete_formulas not found")

        # Upload
        with open(test_doc["docx_path"], "rb") as f:
            docx_content = f.read()

        upload_response = await authenticated_client.post(
            "/api/v1/documents",
            files={
                "file": (
                    test_doc["docx_path"].name,
                    docx_content,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            },
            data={"title": test_doc["title"]},
        )

        assert upload_response.status_code == 201
        doc_id = upload_response.json()["id"]

        # Download semantic IR
        download_response = await authenticated_client.get(
            f"/api/v1/documents/{doc_id}/semantic-ir/download"
        )

        if download_response.status_code == 404:
            pytest.skip("Semantic IR download endpoint not yet implemented")

        assert download_response.status_code == 200, (
            f"Failed to download semantic IR: {download_response.text}"
        )

        # Should be JSON content
        assert download_response.headers.get("content-type") in [
            "application/json",
            "application/json; charset=utf-8"
        ]

        # Should be valid JSON
        ir_data = download_response.json()
        assert "definitions" in ir_data or "formulae" in ir_data or "tables" in ir_data

    @pytest.mark.asyncio
    async def test_semantic_ir_contains_metadata(self, authenticated_client, policy_repository):
        """Test that semantic IR includes document metadata."""
        test_doc = semantic_test_documents[0]

        # Upload
        with open(test_doc["docx_path"], "rb") as f:
            docx_content = f.read()

        upload_response = await authenticated_client.post(
            "/api/v1/documents",
            files={
                "file": (
                    test_doc["docx_path"].name,
                    docx_content,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            },
            data={"title": test_doc["title"]},
        )

        assert upload_response.status_code == 201
        doc_id = upload_response.json()["id"]

        # Get semantic IR
        ir_response = await authenticated_client.get(
            f"/api/v1/documents/{doc_id}/semantic-ir"
        )

        if ir_response.status_code == 404:
            pytest.skip("Semantic IR endpoint not yet implemented")

        assert ir_response.status_code == 200
        ir_data = ir_response.json()

        # Should include metadata fields
        # Based on ADR-014, IR should have document metadata
        assert "document_id" in ir_data or "id" in ir_data
        assert "title" in ir_data or "document_title" in ir_data
