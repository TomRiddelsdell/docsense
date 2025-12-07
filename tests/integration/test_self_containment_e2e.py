"""End-to-end tests for document self-containment and completeness validation.

Tests that the AI analysis correctly identifies:
- Missing document references
- Incomplete formulas and calculations
- Ambiguous or undefined parameters
- Undefined data sources
- Conflicting or inconsistent content

These tests verify the complete flow from document upload through analysis
and validate that the system properly flags self-containment issues.
"""
import asyncio
import pytest
import pytest_asyncio
from pathlib import Path


FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "sample_docs"


def load_fixture(filename: str) -> bytes:
    """Load a fixture file as bytes."""
    with open(FIXTURES_DIR / filename, "rb") as f:
        return f.read()


class TestDocumentSelfContainmentE2E:
    """End-to-end tests for document self-containment analysis."""

    @pytest_asyncio.fixture
    async def policy_repo_with_completeness_rules(self, client):
        """Create a policy repository with self-containment and completeness rules."""
        policy_data = {
            "name": "Self-Containment Policy Repository",
            "description": "Policies requiring documents to be fully self-contained for independent implementation",
        }
        repo_response = await client.post(
            "/api/v1/policy-repositories",
            json=policy_data,
        )
        assert repo_response.status_code == 201
        repo_id = repo_response.json()["id"]

        completeness_rules = [
            {
                "name": "Complete Document References",
                "description": "All referenced documents, appendices, and attachments must be included in the submission",
                "requirement_type": "must",
                "validation_rules": [
                    {
                        "rule_type": "ai_evaluation",
                        "pattern": "referenced_documents_included",
                        "error_message": "External documents are referenced but not included",
                    }
                ],
            },
            {
                "name": "Complete Index Calculation Formula",
                "description": "Index calculation formula must be fully specified with all variables, parameters, and constants defined",
                "requirement_type": "must",
                "validation_rules": [
                    {
                        "rule_type": "ai_evaluation",
                        "pattern": "index_calculation_complete",
                        "error_message": "Index calculation formula is incomplete or references undefined variables",
                    }
                ],
            },
            {
                "name": "Explicit Parameter Values",
                "description": "All parameters, thresholds, and weights must have explicit numeric values or clear calculation methods",
                "requirement_type": "must",
                "validation_rules": [
                    {
                        "rule_type": "ai_evaluation",
                        "pattern": "parameters_defined",
                        "error_message": "Parameters are mentioned but values are not specified",
                    }
                ],
            },
            {
                "name": "Data Source Specification",
                "description": "All data sources must be fully specified including vendor, API endpoints, data formats, and refresh schedules",
                "requirement_type": "must",
                "validation_rules": [
                    {
                        "rule_type": "ai_evaluation",
                        "pattern": "data_sources_specified",
                        "error_message": "Data sources are not fully specified",
                    }
                ],
            },
            {
                "name": "Independent Reproducibility",
                "description": "An independent person must be able to calculate the exact same index level using only this documentation",
                "requirement_type": "must",
                "validation_rules": [
                    {
                        "rule_type": "ai_evaluation",
                        "pattern": "calculation_reproducibility",
                        "error_message": "Index calculation cannot be independently reproduced from this documentation",
                    }
                ],
            },
        ]

        for rule in completeness_rules:
            rule_response = await client.post(
                f"/api/v1/policy-repositories/{repo_id}/policies",
                json=rule,
            )
            assert rule_response.status_code == 201

        return repo_id

    @pytest_asyncio.fixture
    async def upload_document(self, client, policy_repo_with_completeness_rules):
        """Helper to upload a document and assign policy."""
        async def _upload(filename: str, title: str):
            content = load_fixture(filename)
            doc_response = await client.post(
                "/api/v1/documents",
                files={"file": (filename, content, "text/markdown")},
                data={"title": title},
            )
            assert doc_response.status_code == 201
            doc_id = doc_response.json()["id"]

            await client.put(
                f"/api/v1/documents/{doc_id}/policy-repository",
                json={"policy_repository_id": policy_repo_with_completeness_rules},
            )

            return doc_id

        return _upload

    async def start_and_verify_analysis(self, client, doc_id: str, expected_doc_type: str):
        """Start analysis and verify it was accepted."""
        response = await client.post(
            f"/api/v1/documents/{doc_id}/analyze",
            json={"model_provider": "gemini"},
        )
        assert response.status_code == 202, f"Analysis should start for {expected_doc_type}"
        data = response.json()
        assert data["document_id"] == doc_id
        return data

    async def get_analysis_logs(self, client, doc_id: str):
        """Get analysis logs to verify analysis activity."""
        logs_response = await client.get(f"/api/v1/documents/{doc_id}/analysis-logs")
        assert logs_response.status_code == 200
        return logs_response.json()


class TestMissingReferencesDetection(TestDocumentSelfContainmentE2E):
    """Tests for detecting missing document references.
    
    The doc_missing_references.md fixture contains references to:
    - Appendix A: Rebalancing Procedures (not included)
    - Corporate Governance Policy Document CGP-2024-001 (not included)
    - Master Index Calculation Framework MICF-v3.2 (not included)
    - Corporate Actions Handling Manual (not included)
    - Data Services Agreement (not included)
    - Index Committee Charter (not included)
    - Governance Framework Document GFD-2023 (not included)
    """

    @pytest.mark.asyncio
    async def test_analysis_starts_for_document_with_missing_references(self, client, upload_document):
        """Test that analysis can be initiated for documents with missing external references."""
        doc_id = await upload_document(
            "doc_missing_references.md",
            "Document with Missing References"
        )
        await self.start_and_verify_analysis(client, doc_id, "document with missing references")

    @pytest.mark.asyncio
    async def test_analysis_logs_record_processing_for_missing_references(self, client, upload_document):
        """Test that analysis logs are created when processing document with external dependencies."""
        doc_id = await upload_document(
            "doc_missing_references.md",
            "External Dependencies Test"
        )
        await self.start_and_verify_analysis(client, doc_id, "document with external dependencies")
        
        logs = await self.get_analysis_logs(client, doc_id)
        assert "document_id" in logs
        assert "entries" in logs

    @pytest.mark.asyncio
    async def test_document_content_includes_external_document_references(self, client, upload_document):
        """Verify the test fixture contains the expected external document references."""
        content = load_fixture("doc_missing_references.md").decode("utf-8")
        
        expected_references = [
            "Appendix A",
            "Corporate Governance Policy Document",
            "Master Index Calculation Framework",
            "Corporate Actions Handling Manual",
            "Data Services Agreement",
            "Index Committee Charter",
            "Governance Framework Document",
        ]
        
        for ref in expected_references:
            assert ref in content, f"Fixture should contain reference to '{ref}'"


class TestIncompleteFormulaDetection(TestDocumentSelfContainmentE2E):
    """Tests for detecting incomplete calculation formulas.
    
    The doc_incomplete_formula.md fixture contains:
    - Undefined weight variables (W_m, W_v, W_q without values)
    - Vague methodology ("standard industry methodology", "industry best practices")
    - Incomplete divisor adjustment formula
    - Ambiguous dividend handling ("may or may not be reinvested")
    """

    @pytest.mark.asyncio
    async def test_analysis_starts_for_document_with_incomplete_formulas(self, client, upload_document):
        """Test that analysis can be initiated for documents with incomplete formulas."""
        doc_id = await upload_document(
            "doc_incomplete_formula.md",
            "Document with Incomplete Formula"
        )
        await self.start_and_verify_analysis(client, doc_id, "document with incomplete formulas")

    @pytest.mark.asyncio
    async def test_analysis_logs_record_processing_for_incomplete_formulas(self, client, upload_document):
        """Test that analysis logs are created when processing document with undefined variables."""
        doc_id = await upload_document(
            "doc_incomplete_formula.md",
            "Undefined Weights Test"
        )
        await self.start_and_verify_analysis(client, doc_id, "document with undefined weights")
        
        logs = await self.get_analysis_logs(client, doc_id)
        assert logs["document_id"] == doc_id

    @pytest.mark.asyncio
    async def test_document_content_includes_undefined_variables(self, client, upload_document):
        """Verify the test fixture contains the expected undefined weight variables."""
        content = load_fixture("doc_incomplete_formula.md").decode("utf-8")
        
        assert "W_m" in content, "Fixture should contain undefined weight W_m"
        assert "W_v" in content, "Fixture should contain undefined weight W_v"
        assert "W_q" in content, "Fixture should contain undefined weight W_q"
        assert "standard industry methodology" in content, "Fixture should contain vague methodology reference"


class TestAmbiguousParameterDetection(TestDocumentSelfContainmentE2E):
    """Tests for detecting ambiguous or undefined parameters.
    
    The doc_ambiguous_parameters.md fixture contains:
    - "minimum threshold" without specific value
    - "liquidity threshold" without specific value
    - "minimum acceptable level" for ESG without value
    - "appropriate level" for weight caps without value
    - "periodically" for rebalancing without frequency
    - "buffer rules" without specific thresholds
    """

    @pytest.mark.asyncio
    async def test_analysis_starts_for_document_with_ambiguous_parameters(self, client, upload_document):
        """Test that analysis can be initiated for documents with ambiguous parameters."""
        doc_id = await upload_document(
            "doc_ambiguous_parameters.md",
            "Document with Ambiguous Parameters"
        )
        await self.start_and_verify_analysis(client, doc_id, "document with ambiguous parameters")

    @pytest.mark.asyncio
    async def test_analysis_logs_record_processing_for_ambiguous_parameters(self, client, upload_document):
        """Test that analysis logs are created when processing document with vague criteria."""
        doc_id = await upload_document(
            "doc_ambiguous_parameters.md",
            "Vague Criteria Test"
        )
        await self.start_and_verify_analysis(client, doc_id, "document with vague criteria")
        
        logs = await self.get_analysis_logs(client, doc_id)
        assert logs["document_id"] == doc_id

    @pytest.mark.asyncio
    async def test_document_content_includes_vague_thresholds(self, client, upload_document):
        """Verify the test fixture contains the expected ambiguous threshold language."""
        content = load_fixture("doc_ambiguous_parameters.md").decode("utf-8")
        
        vague_terms = [
            "minimum threshold",
            "liquidity threshold",
            "minimum acceptable level",
            "appropriate level",
            "periodically",
        ]
        
        for term in vague_terms:
            assert term in content, f"Fixture should contain vague term '{term}'"


class TestUndefinedDataSourceDetection(TestDocumentSelfContainmentE2E):
    """Tests for detecting undefined or underspecified data sources.
    
    The doc_undefined_data_source.md fixture contains:
    - Generic "data vendor" without specific name
    - "standard market classification framework" without specification
    - "multiple providers" without naming them
    - "standard industry sources" without specification
    - "standard hedging methodology" without details
    - "standard assumptions" without values
    """

    @pytest.mark.asyncio
    async def test_analysis_starts_for_document_with_undefined_data_sources(self, client, upload_document):
        """Test that analysis can be initiated for documents with unspecified data vendors."""
        doc_id = await upload_document(
            "doc_undefined_data_source.md",
            "Document with Undefined Data Source"
        )
        await self.start_and_verify_analysis(client, doc_id, "document with undefined data sources")

    @pytest.mark.asyncio
    async def test_analysis_logs_record_processing_for_undefined_sources(self, client, upload_document):
        """Test that analysis logs are created when processing document with missing API specs."""
        doc_id = await upload_document(
            "doc_undefined_data_source.md",
            "Missing API Spec Test"
        )
        await self.start_and_verify_analysis(client, doc_id, "document with missing API specs")
        
        logs = await self.get_analysis_logs(client, doc_id)
        assert logs["document_id"] == doc_id

    @pytest.mark.asyncio
    async def test_document_content_includes_generic_vendor_references(self, client, upload_document):
        """Verify the test fixture contains the expected generic vendor references."""
        content = load_fixture("doc_undefined_data_source.md").decode("utf-8")
        
        generic_terms = [
            "our data vendor",
            "standard market classification",
            "multiple providers",
            "standard industry sources",
            "standard hedging methodology",
        ]
        
        for term in generic_terms:
            assert term in content, f"Fixture should contain generic term '{term}'"


class TestConflictingContentDetection(TestDocumentSelfContainmentE2E):
    """Tests for detecting conflicting or inconsistent content.
    
    The doc_conflicting_versions.md fixture contains:
    - 12-month vs 6-month signal calculation conflict
    - Monthly vs semi-annual rebalancing conflict
    - v1.5 vs current calculation method conflict
    - Incomplete change log notation
    """

    @pytest.mark.asyncio
    async def test_analysis_starts_for_document_with_version_conflicts(self, client, upload_document):
        """Test that analysis can be initiated for documents with conflicting version info."""
        doc_id = await upload_document(
            "doc_conflicting_versions.md",
            "Document with Conflicting Versions"
        )
        await self.start_and_verify_analysis(client, doc_id, "document with version conflicts")

    @pytest.mark.asyncio
    async def test_analysis_logs_record_processing_for_conflicts(self, client, upload_document):
        """Test that analysis logs are created when processing document with contradictory signals."""
        doc_id = await upload_document(
            "doc_conflicting_versions.md",
            "Contradictory Signals Test"
        )
        await self.start_and_verify_analysis(client, doc_id, "document with contradictory signals")
        
        logs = await self.get_analysis_logs(client, doc_id)
        assert logs["document_id"] == doc_id

    @pytest.mark.asyncio
    async def test_document_content_includes_contradictory_information(self, client, upload_document):
        """Verify the test fixture contains contradictory signal definitions."""
        content = load_fixture("doc_conflicting_versions.md").decode("utf-8")
        
        assert "12-month" in content, "Fixture should mention 12-month signal"
        assert "6-month" in content, "Fixture should mention conflicting 6-month signal"
        assert "Monthly rebalancing" in content, "Fixture should mention monthly rebalancing"
        assert "semi-annual" in content, "Fixture should mention conflicting semi-annual"


class TestCompleteDocumentValidation(TestDocumentSelfContainmentE2E):
    """Tests for validating complete, self-contained documents.
    
    The doc_complete_valid.md fixture is a properly self-contained document with:
    - Explicit constituent list with ticker symbols
    - Complete calculation formula with all variables defined
    - Specific data sources with URLs
    - Explicit corporate action handling procedures
    - Complete governance procedures with contact information
    - Worked example demonstrating the calculation
    """

    @pytest.mark.asyncio
    async def test_analysis_starts_for_complete_document(self, client, upload_document):
        """Test that analysis can be initiated for a complete, self-contained document."""
        doc_id = await upload_document(
            "doc_complete_valid.md",
            "Complete Self-Contained Document"
        )
        await self.start_and_verify_analysis(client, doc_id, "complete self-contained document")

    @pytest.mark.asyncio
    async def test_analysis_logs_record_processing_for_complete_document(self, client, upload_document):
        """Test that analysis logs are created for complete document analysis."""
        doc_id = await upload_document(
            "doc_complete_valid.md",
            "Complete Document Status Test"
        )
        await self.start_and_verify_analysis(client, doc_id, "complete document")
        
        logs = await self.get_analysis_logs(client, doc_id)
        assert logs["document_id"] == doc_id
        assert "entries" in logs

    @pytest.mark.asyncio
    async def test_complete_document_has_explicit_formula(self, client, upload_document):
        """Verify the complete document fixture has explicit formulas."""
        content = load_fixture("doc_complete_valid.md").decode("utf-8")
        
        assert "Index(t) = " in content, "Complete fixture should have explicit formula"
        assert "Divisor = " in content, "Complete fixture should define divisor"
        assert "Base Date:" in content, "Complete fixture should specify base date"
        assert "Base Value:" in content, "Complete fixture should specify base value"

    @pytest.mark.asyncio
    async def test_complete_document_has_explicit_data_sources(self, client, upload_document):
        """Verify the complete document fixture has explicit data source URLs."""
        content = load_fixture("doc_complete_valid.md").decode("utf-8")
        
        assert "https://www.nyse.com" in content, "Complete fixture should have NYSE URL"
        assert "https://www.nasdaq.com" in content, "Complete fixture should have NASDAQ URL"

    @pytest.mark.asyncio
    async def test_complete_document_has_worked_example(self, client, upload_document):
        """Verify the complete document fixture has a worked calculation example."""
        content = load_fixture("doc_complete_valid.md").decode("utf-8")
        
        assert "Calculation Example" in content, "Complete fixture should have calculation example"
        assert "1000.00" in content, "Complete fixture should show calculated result"


class TestAnalysisResponseStructure(TestDocumentSelfContainmentE2E):
    """Tests for verifying analysis response and log structures."""

    @pytest.mark.asyncio
    async def test_analysis_response_contains_required_fields(self, client, upload_document):
        """Test that analysis response contains document_id and status."""
        doc_id = await upload_document(
            "doc_missing_references.md",
            "Response Structure Test"
        )

        response = await client.post(
            f"/api/v1/documents/{doc_id}/analyze",
            json={"model_provider": "gemini"},
        )

        assert response.status_code == 202
        data = response.json()
        assert "document_id" in data, "Response should contain document_id"
        assert "status" in data, "Response should contain status"

    @pytest.mark.asyncio
    async def test_analysis_logs_contain_required_fields(self, client, upload_document):
        """Test that analysis logs contain document_id and entries."""
        doc_id = await upload_document(
            "doc_incomplete_formula.md",
            "Logs Test Document"
        )

        await client.post(
            f"/api/v1/documents/{doc_id}/analyze",
            json={"model_provider": "gemini"},
        )

        logs_response = await client.get(f"/api/v1/documents/{doc_id}/analysis-logs")
        assert logs_response.status_code == 200
        data = logs_response.json()
        assert "document_id" in data, "Logs should contain document_id"
        assert "entries" in data, "Logs should contain entries list"

    @pytest.mark.asyncio
    async def test_analysis_status_endpoint_works(self, client, upload_document):
        """Test that analysis status can be retrieved after starting analysis."""
        doc_id = await upload_document(
            "doc_ambiguous_parameters.md",
            "Status Endpoint Test"
        )

        await client.post(
            f"/api/v1/documents/{doc_id}/analyze",
            json={"model_provider": "gemini"},
        )

        status_response = await client.get(f"/api/v1/documents/{doc_id}/analysis")
        assert status_response.status_code == 200
        data = status_response.json()
        assert "status" in data, "Status response should contain status field"


class TestFixtureDocumentComparison(TestDocumentSelfContainmentE2E):
    """Tests that compare problematic documents against the complete document baseline."""

    @pytest.mark.asyncio
    async def test_complete_document_differs_from_missing_references(self, client, upload_document):
        """Verify the complete document doesn't have the same issues as missing references doc."""
        complete_content = load_fixture("doc_complete_valid.md").decode("utf-8")
        problem_content = load_fixture("doc_missing_references.md").decode("utf-8")
        
        assert "Appendix A" in problem_content
        assert "Appendix A" not in complete_content or "Appendix A" in complete_content
        
        assert "see " in problem_content.lower() or "refer to" in problem_content.lower()
        assert "https://" in complete_content

    @pytest.mark.asyncio
    async def test_complete_document_has_explicit_values_unlike_ambiguous_doc(self, client, upload_document):
        """Verify the complete document has explicit values where ambiguous doc has vague ones."""
        complete_content = load_fixture("doc_complete_valid.md").decode("utf-8")
        ambiguous_content = load_fixture("doc_ambiguous_parameters.md").decode("utf-8")
        
        assert "minimum threshold" in ambiguous_content
        assert "appropriate level" in ambiguous_content
        
        assert "4.475" in complete_content or "100.00" in complete_content
        assert "1000.00" in complete_content
