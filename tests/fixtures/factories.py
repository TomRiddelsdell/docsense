"""Test data factories for generating test fixtures."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from uuid import UUID, uuid4

from src.domain.aggregates.document import Document
from src.domain.aggregates.feedback_session import FeedbackSession
from src.domain.aggregates.policy_repository import PolicyRepository
from src.domain.events.document_events import DocumentUploaded, DocumentConverted
from src.domain.events.analysis_events import AnalysisStarted, AnalysisCompleted
from src.domain.events.feedback_events import FeedbackGenerated, FeedbackSessionCreated
from src.domain.events.policy_events import PolicyRepositoryCreated, PolicyAdded
from src.domain.value_objects import (
    DocumentId,
    ConfidenceScore,
    RequirementType,
    ComplianceStatus,
)


class DocumentFactory:
    """Factory for creating Document test fixtures."""
    
    @staticmethod
    def create(
        document_id: Optional[UUID] = None,
        filename: str = "test_algorithm.pdf",
        content: bytes = b"test content",
        original_format: str = "application/pdf",
        uploaded_by: str = "test@example.com",
    ) -> Document:
        """Create a Document aggregate in UPLOADED state."""
        return Document.upload(
            document_id=document_id or uuid4(),
            filename=filename,
            content=content,
            original_format=original_format,
            uploaded_by=uploaded_by,
        )
    
    @staticmethod
    def create_converted(
        document_id: Optional[UUID] = None,
        filename: str = "test_algorithm.pdf",
        markdown_content: str = "# Test Algorithm\n\nThis is test content.",
        sections: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Document:
        """Create a Document aggregate in CONVERTED state."""
        doc = DocumentFactory.create(document_id=document_id, filename=filename)
        doc.convert(
            markdown_content=markdown_content,
            sections=sections or [{"heading": "Test Algorithm", "content": "This is test content.", "level": 1}],
            metadata=metadata or {"word_count": 5, "page_count": 1},
        )
        return doc
    
    @staticmethod
    def create_analyzed(
        document_id: Optional[UUID] = None,
        filename: str = "test_algorithm.pdf",
        policy_repository_id: Optional[UUID] = None,
        findings_count: int = 3,
        compliance_score: float = 0.85,
        ai_model: str = "gemini-pro",
    ) -> Document:
        """Create a Document aggregate in ANALYZED state."""
        doc = DocumentFactory.create_converted(document_id=document_id, filename=filename)
        policy_id = policy_repository_id or uuid4()
        
        doc.start_analysis(
            policy_repository_id=policy_id,
            ai_model=ai_model,
            initiated_by="test@example.com",
        )
        doc.complete_analysis(
            findings_count=findings_count,
            compliance_score=compliance_score,
            findings=[{"type": "issue", "description": f"Issue {i}"} for i in range(findings_count)],
            processing_time_ms=1500,
        )
        return doc

    @staticmethod
    def create_events(
        document_id: Optional[UUID] = None,
        include_conversion: bool = True,
        include_analysis: bool = False,
    ) -> List[Union[DocumentUploaded, DocumentConverted, AnalysisStarted, AnalysisCompleted]]:
        """Create a list of document events."""
        doc_id = document_id or uuid4()
        events: List[Union[DocumentUploaded, DocumentConverted, AnalysisStarted, AnalysisCompleted]] = [
            DocumentUploaded(
                aggregate_id=doc_id,
                filename="test.pdf",
                original_format="application/pdf",
                file_size_bytes=1024,
                uploaded_by="test@example.com",
            )
        ]
        
        if include_conversion:
            events.append(
                DocumentConverted(
                    aggregate_id=doc_id,
                    markdown_content="# Test\n\nContent here.",
                    sections=[{"heading": "Test", "content": "Content here.", "level": 1}],
                    metadata={"word_count": 3},
                    conversion_warnings=[],
                )
            )
        
        if include_analysis:
            policy_id = uuid4()
            events.append(
                AnalysisStarted(
                    aggregate_id=doc_id,
                    policy_repository_id=policy_id,
                    ai_model="gemini-pro",
                    initiated_by="test@example.com",
                )
            )
            events.append(
                AnalysisCompleted(
                    aggregate_id=doc_id,
                    findings_count=2,
                    compliance_score=0.85,
                    findings=[{"type": "issue", "description": "Issue 1"}, {"type": "issue", "description": "Issue 2"}],
                    processing_time_ms=1200,
                )
            )
        
        return events


class FeedbackFactory:
    """Factory for creating FeedbackSession test fixtures."""
    
    @staticmethod
    def create(
        session_id: Optional[UUID] = None,
        document_id: Optional[UUID] = None,
    ) -> FeedbackSession:
        """Create a FeedbackSession aggregate."""
        return FeedbackSession.create_for_document(
            session_id=session_id or uuid4(),
            document_id=document_id or uuid4(),
        )
    
    @staticmethod
    def create_with_feedback(
        session_id: Optional[UUID] = None,
        document_id: Optional[UUID] = None,
        feedback_count: int = 3,
    ) -> FeedbackSession:
        """Create a FeedbackSession with generated feedback items."""
        session = FeedbackFactory.create(
            session_id=session_id,
            document_id=document_id,
        )
        
        for i in range(feedback_count):
            session.add_feedback(
                feedback_id=uuid4(),
                issue_description=f"Test issue {i + 1} description",
                suggested_change=f"Suggested change {i + 1}",
                confidence_score=0.85 - (i * 0.05),
                policy_reference=f"SEC-{100 + i}",
                section_reference=f"Section {i + 1}",
            )
        
        return session
    
    @staticmethod
    def create_feedback_data(
        section_reference: str = "Entry Conditions",
        issue_description: str = "Missing parameter definition",
    ) -> Dict[str, Any]:
        """Create feedback data dictionary."""
        return {
            "issue_description": issue_description,
            "suggested_change": "RSI(14) crosses above 30 and remains for 2 bars",
            "confidence_score": 0.87,
            "policy_reference": "SEC-001",
            "section_reference": section_reference,
        }


class PolicyFactory:
    """Factory for creating PolicyRepository test fixtures."""
    
    @staticmethod
    def create(
        repository_id: Optional[UUID] = None,
        name: str = "SEC Index Publishing Requirements",
        description: str = "Requirements for SEC-compliant index methodology documents",
        created_by: str = "admin@example.com",
    ) -> PolicyRepository:
        """Create a PolicyRepository aggregate."""
        return PolicyRepository.create(
            repository_id=repository_id or uuid4(),
            name=name,
            description=description,
            created_by=created_by,
        )
    
    @staticmethod
    def create_with_policies(
        repository_id: Optional[UUID] = None,
        policy_count: int = 3,
    ) -> PolicyRepository:
        """Create a PolicyRepository with policies added."""
        repo = PolicyFactory.create(repository_id=repository_id)
        
        policy_templates = [
            ("Entry Exit Clarity", "All entry and exit conditions must be clearly defined", "MUST"),
            ("Parameter Definitions", "All parameters must have explicit definitions", "MUST"),
            ("Risk Disclosure", "Risk factors should be documented", "SHOULD"),
            ("Performance Metrics", "Historical performance metrics may be included", "MAY"),
        ]
        
        for i in range(min(policy_count, len(policy_templates))):
            name, content, req_type = policy_templates[i]
            repo.add_policy(
                policy_id=uuid4(),
                policy_name=name,
                policy_content=content,
                requirement_type=req_type,
                added_by="admin@example.com",
            )
        
        return repo
    
    @staticmethod
    def create_policy_data(
        policy_name: str = "Test Policy",
        requirement_type: str = "MUST",
    ) -> Dict[str, Any]:
        """Create policy data dictionary."""
        return {
            "policy_name": policy_name,
            "policy_content": f"Description for {policy_name}",
            "requirement_type": requirement_type,
        }


class EventFactory:
    """Factory for creating domain event test fixtures."""
    
    @staticmethod
    def document_uploaded(
        aggregate_id: Optional[UUID] = None,
        filename: str = "test.pdf",
        original_format: str = "application/pdf",
        file_size_bytes: int = 1024,
        uploaded_by: str = "test@example.com",
    ) -> DocumentUploaded:
        """Create a DocumentUploaded event."""
        return DocumentUploaded(
            aggregate_id=aggregate_id or uuid4(),
            filename=filename,
            original_format=original_format,
            file_size_bytes=file_size_bytes,
            uploaded_by=uploaded_by,
        )
    
    @staticmethod
    def document_converted(
        aggregate_id: Optional[UUID] = None,
        markdown_content: str = "# Test\n\nContent",
        sections: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DocumentConverted:
        """Create a DocumentConverted event."""
        return DocumentConverted(
            aggregate_id=aggregate_id or uuid4(),
            markdown_content=markdown_content,
            sections=sections or [{"heading": "Test", "content": "Content", "level": 1}],
            metadata=metadata or {"word_count": 2},
            conversion_warnings=[],
        )
    
    @staticmethod
    def analysis_started(
        aggregate_id: Optional[UUID] = None,
        policy_repository_id: Optional[UUID] = None,
        ai_model: str = "gemini-pro",
        initiated_by: str = "test@example.com",
    ) -> AnalysisStarted:
        """Create an AnalysisStarted event."""
        return AnalysisStarted(
            aggregate_id=aggregate_id or uuid4(),
            policy_repository_id=policy_repository_id or uuid4(),
            ai_model=ai_model,
            initiated_by=initiated_by,
        )
    
    @staticmethod
    def analysis_completed(
        aggregate_id: Optional[UUID] = None,
        findings_count: int = 3,
        compliance_score: float = 0.85,
        findings: Optional[List[Dict[str, Any]]] = None,
        processing_time_ms: int = 1500,
    ) -> AnalysisCompleted:
        """Create an AnalysisCompleted event."""
        return AnalysisCompleted(
            aggregate_id=aggregate_id or uuid4(),
            findings_count=findings_count,
            compliance_score=compliance_score,
            findings=findings or [{"type": "issue", "description": f"Issue {i}"} for i in range(findings_count)],
            processing_time_ms=processing_time_ms,
        )
    
    @staticmethod
    def feedback_generated(
        aggregate_id: Optional[UUID] = None,
        feedback_id: Optional[UUID] = None,
        issue_description: str = "Test issue description",
        suggested_change: str = "Suggested text here",
        confidence_score: float = 0.85,
        policy_reference: str = "SEC-001",
        section_reference: str = "Entry Conditions",
    ) -> FeedbackGenerated:
        """Create a FeedbackGenerated event."""
        return FeedbackGenerated(
            aggregate_id=aggregate_id or uuid4(),
            feedback_id=feedback_id or uuid4(),
            issue_description=issue_description,
            suggested_change=suggested_change,
            confidence_score=confidence_score,
            policy_reference=policy_reference,
            section_reference=section_reference,
        )
    
    @staticmethod
    def policy_repository_created(
        aggregate_id: Optional[UUID] = None,
        name: str = "Test Repository",
        description: str = "Test repository description",
        created_by: str = "admin@example.com",
    ) -> PolicyRepositoryCreated:
        """Create a PolicyRepositoryCreated event."""
        return PolicyRepositoryCreated(
            aggregate_id=aggregate_id or uuid4(),
            name=name,
            description=description,
            created_by=created_by,
        )
    
    @staticmethod
    def feedback_session_created(
        aggregate_id: Optional[UUID] = None,
        document_id: Optional[UUID] = None,
    ) -> FeedbackSessionCreated:
        """Create a FeedbackSessionCreated event."""
        return FeedbackSessionCreated(
            aggregate_id=aggregate_id or uuid4(),
            document_id=document_id or uuid4(),
        )
    
    @staticmethod
    def policy_added(
        aggregate_id: Optional[UUID] = None,
        policy_id: Optional[UUID] = None,
        policy_name: str = "Test Policy",
        policy_content: str = "Test policy content",
        requirement_type: str = "MUST",
        added_by: str = "admin@example.com",
    ) -> PolicyAdded:
        """Create a PolicyAdded event."""
        return PolicyAdded(
            aggregate_id=aggregate_id or uuid4(),
            policy_id=policy_id or uuid4(),
            policy_name=policy_name,
            policy_content=policy_content,
            requirement_type=requirement_type,
            added_by=added_by,
        )
