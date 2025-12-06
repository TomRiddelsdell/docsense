import pytest
from uuid import uuid4, UUID
from typing import Optional

from src.domain.commands.base import Command
from src.domain.commands.document_commands import (
    UploadDocument,
    ExportDocument,
    DeleteDocument,
)
from src.domain.commands.analysis_commands import (
    StartAnalysis,
    CancelAnalysis,
)
from src.domain.commands.feedback_commands import (
    AcceptChange,
    RejectChange,
    ModifyChange,
)
from src.domain.commands.policy_commands import (
    CreatePolicyRepository,
    AddPolicy,
    AssignDocumentToPolicy,
)


class TestCommand:
    def test_command_has_unique_id(self):
        cmd1 = Command()
        cmd2 = Command()
        assert cmd1.command_id != cmd2.command_id

    def test_command_is_immutable(self):
        cmd = Command()
        with pytest.raises(AttributeError):
            cmd.command_id = uuid4()


class TestUploadDocument:
    def test_create_upload_document_command(self):
        content = b"document content"
        cmd = UploadDocument(
            filename="algorithm.docx",
            content=content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            uploaded_by="user@example.com",
        )
        assert cmd.filename == "algorithm.docx"
        assert cmd.content == content
        assert cmd.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert cmd.uploaded_by == "user@example.com"

    def test_upload_with_policy_repository(self):
        policy_repo_id = uuid4()
        cmd = UploadDocument(
            filename="algorithm.pdf",
            content=b"pdf content",
            content_type="application/pdf",
            uploaded_by="user@example.com",
            policy_repository_id=policy_repo_id,
        )
        assert cmd.policy_repository_id == policy_repo_id


class TestExportDocument:
    def test_create_export_document_command(self):
        document_id = uuid4()
        cmd = ExportDocument(
            document_id=document_id,
            export_format="docx",
            exported_by="user@example.com",
        )
        assert cmd.document_id == document_id
        assert cmd.export_format == "docx"
        assert cmd.exported_by == "user@example.com"

    def test_export_with_version(self):
        document_id = uuid4()
        cmd = ExportDocument(
            document_id=document_id,
            export_format="pdf",
            exported_by="user@example.com",
            version="1.2.0",
        )
        assert cmd.version == "1.2.0"


class TestDeleteDocument:
    def test_create_delete_document_command(self):
        document_id = uuid4()
        cmd = DeleteDocument(
            document_id=document_id,
            deleted_by="admin@example.com",
            reason="Duplicate document",
        )
        assert cmd.document_id == document_id
        assert cmd.deleted_by == "admin@example.com"
        assert cmd.reason == "Duplicate document"


class TestStartAnalysis:
    def test_create_start_analysis_command(self):
        document_id = uuid4()
        policy_repository_id = uuid4()
        cmd = StartAnalysis(
            document_id=document_id,
            policy_repository_id=policy_repository_id,
            initiated_by="user@example.com",
        )
        assert cmd.document_id == document_id
        assert cmd.policy_repository_id == policy_repository_id
        assert cmd.initiated_by == "user@example.com"

    def test_start_analysis_with_ai_model(self):
        cmd = StartAnalysis(
            document_id=uuid4(),
            policy_repository_id=uuid4(),
            initiated_by="user@example.com",
            ai_model="claude-3-opus",
        )
        assert cmd.ai_model == "claude-3-opus"

    def test_start_analysis_default_ai_model(self):
        cmd = StartAnalysis(
            document_id=uuid4(),
            policy_repository_id=uuid4(),
            initiated_by="user@example.com",
        )
        assert cmd.ai_model == "gemini-pro"


class TestCancelAnalysis:
    def test_create_cancel_analysis_command(self):
        document_id = uuid4()
        cmd = CancelAnalysis(
            document_id=document_id,
            cancelled_by="user@example.com",
            reason="Taking too long",
        )
        assert cmd.document_id == document_id
        assert cmd.cancelled_by == "user@example.com"
        assert cmd.reason == "Taking too long"


class TestAcceptChange:
    def test_create_accept_change_command(self):
        document_id = uuid4()
        feedback_id = uuid4()
        cmd = AcceptChange(
            document_id=document_id,
            feedback_id=feedback_id,
            accepted_by="user@example.com",
        )
        assert cmd.document_id == document_id
        assert cmd.feedback_id == feedback_id
        assert cmd.accepted_by == "user@example.com"


class TestRejectChange:
    def test_create_reject_change_command(self):
        document_id = uuid4()
        feedback_id = uuid4()
        cmd = RejectChange(
            document_id=document_id,
            feedback_id=feedback_id,
            rejected_by="user@example.com",
            reason="Not applicable to this context",
        )
        assert cmd.document_id == document_id
        assert cmd.feedback_id == feedback_id
        assert cmd.rejected_by == "user@example.com"
        assert cmd.reason == "Not applicable to this context"


class TestModifyChange:
    def test_create_modify_change_command(self):
        document_id = uuid4()
        feedback_id = uuid4()
        cmd = ModifyChange(
            document_id=document_id,
            feedback_id=feedback_id,
            modified_by="user@example.com",
            modified_content="Updated risk disclosure with specific examples",
        )
        assert cmd.document_id == document_id
        assert cmd.feedback_id == feedback_id
        assert cmd.modified_by == "user@example.com"
        assert cmd.modified_content == "Updated risk disclosure with specific examples"


class TestCreatePolicyRepository:
    def test_create_policy_repository_command(self):
        cmd = CreatePolicyRepository(
            name="SEC Compliance Policies",
            description="Policies for SEC regulatory compliance",
            created_by="admin@example.com",
        )
        assert cmd.name == "SEC Compliance Policies"
        assert cmd.description == "Policies for SEC regulatory compliance"
        assert cmd.created_by == "admin@example.com"


class TestAddPolicy:
    def test_create_add_policy_command(self):
        repository_id = uuid4()
        cmd = AddPolicy(
            repository_id=repository_id,
            policy_name="Risk Disclosure Requirements",
            policy_content="All documents must include risk disclosure...",
            requirement_type="MUST",
            added_by="admin@example.com",
        )
        assert cmd.repository_id == repository_id
        assert cmd.policy_name == "Risk Disclosure Requirements"
        assert cmd.requirement_type == "MUST"


class TestAssignDocumentToPolicy:
    def test_create_assign_document_command(self):
        repository_id = uuid4()
        document_id = uuid4()
        cmd = AssignDocumentToPolicy(
            repository_id=repository_id,
            document_id=document_id,
            assigned_by="user@example.com",
        )
        assert cmd.repository_id == repository_id
        assert cmd.document_id == document_id
        assert cmd.assigned_by == "user@example.com"
