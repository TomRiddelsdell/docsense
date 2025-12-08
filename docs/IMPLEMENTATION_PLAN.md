# Implementation Plan: From Foundation to Production

## Executive Summary

This document provides a comprehensive, step-by-step plan to evolve the Trading Algorithm Document Analyzer from its current foundation state to a polished, production-ready application. The plan emphasizes:

- **Domain-Driven Design (DDD)** principles throughout
- **Effective test infrastructure** following testing best practices
- **High-quality code** with modularity and clarity

---

## Current State Assessment

### Completed Foundation
| Component | Status | Location |
|-----------|--------|----------|
| OpenAPI Specification | Complete | `docs/api/openapi.yaml` |
| Database Schema (Event Store) | Complete | `docs/database/event_store_schema.sql` |
| React Frontend Shell | Complete | `client/` |
| Document Converters | Complete | `src/infrastructure/converters/` |
| Policy Repository Templates | Complete | `docs/templates/policy-repositories/` |
| Architecture Decision Records | Complete | `docs/decisions/` |

### What Remains
1. Domain Layer (Aggregates, Events, Commands, Value Objects)
2. Application Layer (Command Handlers, Query Handlers)
3. Infrastructure Layer (Event Store, Repositories, Projections)
4. API Layer (FastAPI Routes, DTOs)
5. AI Agent Integration
6. Frontend Feature Implementation
7. Test Infrastructure
8. Production Hardening

---

## Phase 1: Domain Layer Implementation

**Duration**: 2-3 weeks  
**Goal**: Implement the core domain model following strict DDD principles

### 1.1 Value Objects

Value Objects are immutable, identity-less domain concepts.

**Files to Create**:
```
src/domain/value_objects/
├── __init__.py
├── document_id.py          # UUID wrapper with validation
├── version_number.py       # Semantic versioning (major.minor.patch)
├── content.py              # Document content with format info
├── section.py              # Document section with heading/content
├── feedback_id.py          # UUID wrapper for feedback items
├── confidence_score.py     # 0.0-1.0 range with validation
├── policy_id.py            # UUID wrapper for policies
├── requirement_type.py     # MUST/SHOULD/MAY enum
├── compliance_status.py    # PENDING/COMPLIANT/PARTIAL/NON_COMPLIANT
└── audit_entry.py          # Timestamp + action + actor
```

**Implementation Guidelines**:
- All value objects are immutable (use `@dataclass(frozen=True)` or `__slots__`)
- Validation in `__init__` or factory methods
- Equality based on values, not identity
- No side effects in methods

**Example Pattern**:
```python
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class DocumentId:
    value: UUID
    
    @classmethod
    def generate(cls) -> "DocumentId":
        return cls(uuid4())
    
    @classmethod
    def from_string(cls, value: str) -> "DocumentId":
        return cls(UUID(value))
    
    def __str__(self) -> str:
        return str(self.value)
```

### 1.2 Domain Events

Events are immutable records of what happened. Named in past tense.

**Files to Create**:
```
src/domain/events/
├── __init__.py
├── base.py                 # Base DomainEvent class
├── document_events.py      # DocumentUploaded, DocumentConverted, DocumentExported
├── analysis_events.py      # AnalysisStarted, AnalysisCompleted, AnalysisFailed
├── feedback_events.py      # FeedbackGenerated, ChangeAccepted, ChangeRejected
├── policy_events.py        # PolicyRepositoryCreated, PolicyAdded, DocumentAssigned
└── audit_events.py         # AuditEntryRecorded
```

**Base Event Structure**:
```python
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: UUID = field(default=None)
    aggregate_type: str = field(default="")
    version: int = field(default=1)
    
    @property
    def event_type(self) -> str:
        return self.__class__.__name__
```

**Document Events**:
```python
@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    aggregate_type: str = field(default="Document")
    filename: str = ""
    original_format: str = ""
    file_size_bytes: int = 0
    uploaded_by: str = ""

@dataclass(frozen=True)
class DocumentConverted(DomainEvent):
    aggregate_type: str = field(default="Document")
    markdown_content: str = ""
    sections: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    conversion_warnings: list = field(default_factory=list)
```

### 1.3 Commands

Commands are instructions to change state. Named imperatively.

**Files to Create**:
```
src/domain/commands/
├── __init__.py
├── base.py                 # Base Command class
├── document_commands.py    # UploadDocument, ExportDocument, DeleteDocument
├── analysis_commands.py    # StartAnalysis, CancelAnalysis
├── feedback_commands.py    # AcceptChange, RejectChange, ModifyChange
└── policy_commands.py      # CreatePolicyRepository, AddPolicy, AssignDocument
```

**Example Commands**:
```python
@dataclass(frozen=True)
class UploadDocument:
    filename: str
    content: bytes
    content_type: str
    uploaded_by: str
    policy_repository_id: Optional[UUID] = None

@dataclass(frozen=True)
class AcceptChange:
    document_id: UUID
    feedback_id: UUID
    accepted_by: str
```

### 1.4 Domain Aggregates

Aggregates are consistency boundaries that encapsulate domain logic.

**Files to Create**:
```
src/domain/aggregates/
├── __init__.py
├── base.py                 # Base Aggregate class with event sourcing support
├── document.py             # Document aggregate
├── feedback_session.py     # FeedbackSession aggregate
├── policy_repository.py    # PolicyRepository aggregate
└── audit_trail.py          # AuditTrail aggregate
```

**Base Aggregate Pattern**:
```python
from abc import ABC, abstractmethod
from typing import List
from uuid import UUID

class Aggregate(ABC):
    def __init__(self, aggregate_id: UUID):
        self._id = aggregate_id
        self._version = 0
        self._pending_events: List[DomainEvent] = []
    
    @property
    def id(self) -> UUID:
        return self._id
    
    @property
    def version(self) -> int:
        return self._version
    
    @property
    def pending_events(self) -> List[DomainEvent]:
        return self._pending_events.copy()
    
    def clear_pending_events(self) -> List[DomainEvent]:
        events = self._pending_events.copy()
        self._pending_events.clear()
        return events
    
    def _apply_event(self, event: DomainEvent, is_new: bool = True) -> None:
        self._when(event)
        self._version += 1
        if is_new:
            self._pending_events.append(event)
    
    @abstractmethod
    def _when(self, event: DomainEvent) -> None:
        """Apply event to aggregate state."""
        pass
    
    @classmethod
    def reconstitute(cls, events: List[DomainEvent]) -> "Aggregate":
        """Rebuild aggregate from event history."""
        if not events:
            raise ValueError("Cannot reconstitute from empty events")
        
        aggregate = cls.__new__(cls)
        aggregate._id = events[0].aggregate_id
        aggregate._version = 0
        aggregate._pending_events = []
        
        for event in events:
            aggregate._apply_event(event, is_new=False)
        
        return aggregate
```

**Document Aggregate**:
```python
class Document(Aggregate):
    def __init__(self, document_id: UUID):
        super().__init__(document_id)
        self._filename: str = ""
        self._original_format: str = ""
        self._markdown_content: str = ""
        self._sections: List[Section] = []
        self._current_version: VersionNumber = VersionNumber(1, 0, 0)
        self._status: DocumentStatus = DocumentStatus.DRAFT
        self._policy_repository_id: Optional[UUID] = None
    
    # Factory method for creating new documents
    @classmethod
    def upload(
        cls,
        document_id: UUID,
        filename: str,
        content: bytes,
        original_format: str,
        uploaded_by: str
    ) -> "Document":
        document = cls(document_id)
        document._apply_event(DocumentUploaded(
            aggregate_id=document_id,
            filename=filename,
            original_format=original_format,
            file_size_bytes=len(content),
            uploaded_by=uploaded_by
        ))
        return document
    
    def convert(self, markdown_content: str, sections: List[dict], metadata: dict) -> None:
        self._apply_event(DocumentConverted(
            aggregate_id=self._id,
            markdown_content=markdown_content,
            sections=sections,
            metadata=metadata
        ))
    
    def _when(self, event: DomainEvent) -> None:
        match event:
            case DocumentUploaded():
                self._filename = event.filename
                self._original_format = event.original_format
                self._status = DocumentStatus.UPLOADED
            case DocumentConverted():
                self._markdown_content = event.markdown_content
                self._sections = [Section(**s) for s in event.sections]
                self._status = DocumentStatus.CONVERTED
            # ... handle other events
```

### 1.5 Domain Services

Domain services contain logic that doesn't naturally fit in aggregates.

**Files to Create**:
```
src/domain/services/
├── __init__.py
├── document_conversion_service.py  # Orchestrates document conversion
├── compliance_checker.py           # Checks document against policies
└── version_calculator.py           # Determines next version number
```

### 1.6 Domain Exceptions

Custom exceptions for domain rule violations.

**Files to Create**:
```
src/domain/exceptions/
├── __init__.py
├── document_exceptions.py    # DocumentNotFound, InvalidDocumentFormat
├── analysis_exceptions.py    # AnalysisInProgress, AnalysisFailed
├── feedback_exceptions.py    # FeedbackNotFound, ChangeAlreadyProcessed
└── policy_exceptions.py      # PolicyRepositoryNotFound, InvalidPolicy
```

---

## Phase 2: Infrastructure Layer Implementation

**Duration**: 2-3 weeks  
**Goal**: Implement persistence, repositories, and external integrations

### 2.1 Event Store Implementation

**Files to Create**:
```
src/infrastructure/persistence/
├── __init__.py
├── event_store.py              # PostgreSQL event store implementation
├── event_serializer.py         # JSON serialization for events
├── snapshot_store.py           # Aggregate snapshots for performance
└── connection.py               # Database connection management
```

**Event Store Interface**:
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

class EventStore(ABC):
    @abstractmethod
    async def append(
        self,
        aggregate_id: UUID,
        events: List[DomainEvent],
        expected_version: int
    ) -> None:
        """Append events with optimistic concurrency."""
        pass
    
    @abstractmethod
    async def get_events(
        self,
        aggregate_id: UUID,
        from_version: int = 0
    ) -> List[DomainEvent]:
        """Get all events for an aggregate."""
        pass
    
    @abstractmethod
    async def get_all_events(
        self,
        from_position: int = 0,
        batch_size: int = 100
    ) -> List[DomainEvent]:
        """Get all events for projections."""
        pass
```

**PostgreSQL Implementation**:
```python
class PostgresEventStore(EventStore):
    async def append(
        self,
        aggregate_id: UUID,
        events: List[DomainEvent],
        expected_version: int
    ) -> None:
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Check current version (optimistic concurrency)
                current = await conn.fetchval(
                    "SELECT MAX(version) FROM events WHERE aggregate_id = $1",
                    aggregate_id
                )
                if (current or 0) != expected_version:
                    raise ConcurrencyError(
                        f"Expected version {expected_version}, got {current}"
                    )
                
                # Append new events
                for i, event in enumerate(events):
                    await conn.execute(
                        """
                        INSERT INTO events 
                        (event_id, aggregate_id, aggregate_type, event_type, 
                         version, data, metadata, occurred_at)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        event.event_id,
                        aggregate_id,
                        event.aggregate_type,
                        event.event_type,
                        expected_version + i + 1,
                        self._serializer.serialize(event),
                        {},
                        event.occurred_at
                    )
```

### 2.2 Repositories

Repositories provide aggregate persistence.

**Files to Create**:
```
src/infrastructure/repositories/
├── __init__.py
├── base.py                     # Base repository with event sourcing
├── document_repository.py      # Document aggregate repository
├── feedback_repository.py      # FeedbackSession repository
├── policy_repository.py        # PolicyRepository aggregate repository
└── audit_repository.py         # AuditTrail repository
```

**Repository Pattern**:
```python
class Repository(ABC, Generic[T]):
    def __init__(self, event_store: EventStore, snapshot_store: SnapshotStore):
        self._event_store = event_store
        self._snapshot_store = snapshot_store
    
    @abstractmethod
    def _aggregate_type(self) -> Type[T]:
        pass
    
    async def get(self, aggregate_id: UUID) -> Optional[T]:
        # Try snapshot first
        snapshot = await self._snapshot_store.get(aggregate_id)
        from_version = snapshot.version if snapshot else 0
        
        events = await self._event_store.get_events(aggregate_id, from_version)
        
        if not events and not snapshot:
            return None
        
        if snapshot:
            aggregate = snapshot.aggregate
            for event in events:
                aggregate._apply_event(event, is_new=False)
            return aggregate
        
        return self._aggregate_type().reconstitute(events)
    
    async def save(self, aggregate: T) -> None:
        events = aggregate.clear_pending_events()
        if events:
            await self._event_store.append(
                aggregate.id,
                events,
                aggregate.version - len(events)
            )
```

### 2.3 Projections

Projections build read models from events.

**Files to Create**:
```
src/infrastructure/projections/
├── __init__.py
├── base.py                     # Base projection class
├── document_projector.py       # Builds DocumentView
├── feedback_projector.py       # Builds FeedbackView
├── audit_projector.py          # Builds AuditLogView
├── policy_projector.py         # Builds PolicyView
└── projection_manager.py       # Manages projection subscriptions
```

**Projection Pattern**:
```python
class Projection(ABC):
    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """Process event and update read model."""
        pass
    
    @abstractmethod
    def handles(self) -> List[Type[DomainEvent]]:
        """List of event types this projection handles."""
        pass

class DocumentProjection(Projection):
    def __init__(self, db_pool):
        self._pool = db_pool
    
    def handles(self) -> List[Type[DomainEvent]]:
        return [DocumentUploaded, DocumentConverted, DocumentExported]
    
    async def handle(self, event: DomainEvent) -> None:
        match event:
            case DocumentUploaded():
                await self._insert_document(event)
            case DocumentConverted():
                await self._update_document_content(event)
            case DocumentExported():
                await self._record_export(event)
    
    async def _insert_document(self, event: DocumentUploaded) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO documents_view 
                (id, filename, original_format, status, uploaded_at, uploaded_by)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                event.aggregate_id,
                event.filename,
                event.original_format,
                "uploaded",
                event.occurred_at,
                event.uploaded_by
            )
```

### 2.4 Read Model Queries

Query services for read models.

**Files to Create**:
```
src/infrastructure/queries/
├── __init__.py
├── document_queries.py         # DocumentView queries
├── feedback_queries.py         # FeedbackView queries
├── audit_queries.py            # AuditLogView queries
├── policy_queries.py           # PolicyView queries
└── search_queries.py           # Full-text search queries
```

---

## Phase 3: Application Layer Implementation

**Duration**: 2-3 weeks  
**Goal**: Implement command and query handlers

### 3.1 Command Handlers

**Files to Create**:
```
src/application/commands/
├── __init__.py
├── base.py                     # Base handler and dispatcher
├── document_handlers.py        # UploadDocument, ExportDocument handlers
├── analysis_handlers.py        # StartAnalysis, CancelAnalysis handlers
├── feedback_handlers.py        # AcceptChange, RejectChange handlers
└── policy_handlers.py          # CreateRepository, AddPolicy handlers
```

**Handler Pattern**:
```python
class CommandHandler(ABC, Generic[TCommand, TResult]):
    @abstractmethod
    async def handle(self, command: TCommand) -> TResult:
        pass

class UploadDocumentHandler(CommandHandler[UploadDocument, DocumentId]):
    def __init__(
        self,
        document_repository: DocumentRepository,
        converter_factory: ConverterFactory,
        event_publisher: EventPublisher
    ):
        self._documents = document_repository
        self._converters = converter_factory
        self._publisher = event_publisher
    
    async def handle(self, command: UploadDocument) -> DocumentId:
        # Generate ID
        document_id = DocumentId.generate()
        
        # Create aggregate and apply upload
        document = Document.upload(
            document_id=document_id.value,
            filename=command.filename,
            content=command.content,
            original_format=command.content_type,
            uploaded_by=command.uploaded_by
        )
        
        # Convert document
        converter = self._converters.get_converter(command.content_type)
        result = converter.convert_from_bytes(command.content, command.filename)
        
        if result.success:
            document.convert(
                markdown_content=result.markdown_content,
                sections=[s.__dict__ for s in result.sections],
                metadata=result.metadata.__dict__
            )
        
        # Persist
        await self._documents.save(document)
        
        # Publish events
        for event in document.pending_events:
            await self._publisher.publish(event)
        
        return document_id
```

### 3.2 Query Handlers

**Files to Create**:
```
src/application/queries/
├── __init__.py
├── base.py                     # Base query handler
├── document_queries.py         # GetDocument, ListDocuments handlers
├── feedback_queries.py         # GetFeedback, ListPendingFeedback handlers
├── audit_queries.py            # GetAuditTrail handlers
└── policy_queries.py           # GetPolicyRepository, ListPolicies handlers
```

### 3.3 Application Services

Cross-cutting application concerns.

**Files Created**:
```
src/application/services/
├── __init__.py
├── unit_of_work.py             # Transaction management (UnitOfWork, PostgresUnitOfWork, InMemoryUnitOfWork)
└── event_publisher.py          # Publishes events to projections (EventPublisher, InMemoryEventPublisher)
```

Note: High-level document and analysis orchestration is handled by command handlers rather than separate service classes. This keeps the application layer focused on CQRS patterns where commands coordinate domain operations.

---

## Phase 4: AI Agent Integration

**Duration**: 2-3 weeks  
**Goal**: Implement multi-model AI analysis

### 4.1 AI Provider Abstraction

**Files to Create**:
```
src/infrastructure/ai/
├── __init__.py
├── base.py                     # AIProvider interface
├── gemini_provider.py          # Google Gemini implementation
├── openai_provider.py          # OpenAI implementation
├── claude_provider.py          # Anthropic Claude implementation
├── provider_factory.py         # Creates providers based on config
└── rate_limiter.py             # API rate limiting
```

**Provider Interface**:
```python
class AIProvider(ABC):
    @abstractmethod
    async def analyze_document(
        self,
        content: str,
        policy_rules: List[PolicyRule],
        options: AnalysisOptions
    ) -> AnalysisResult:
        pass
    
    @abstractmethod
    async def generate_suggestion(
        self,
        issue: str,
        context: str,
        policy: Policy
    ) -> Suggestion:
        pass
```

### 4.2 Analysis Engine

**Files to Create**:
```
src/infrastructure/ai/analysis/
├── __init__.py
├── engine.py                   # Main analysis orchestrator
├── policy_evaluator.py         # Evaluates document against policies
├── feedback_generator.py       # Generates actionable feedback
├── progress_tracker.py         # Tracks long-running analysis
└── result_aggregator.py        # Combines results from multiple passes
```

### 4.3 Prompt Templates

**Files to Create**:
```
src/infrastructure/ai/prompts/
├── __init__.py
├── base.py                     # Prompt template base
├── document_analysis.py        # Document analysis prompts
├── policy_compliance.py        # Policy compliance prompts
└── suggestion_generation.py    # Suggestion generation prompts
```

---

## Phase 5: API Layer Implementation

**Duration**: 2 weeks  
**Goal**: Implement FastAPI routes following OpenAPI spec

### 5.1 API Structure

**Files to Create**:
```
src/api/
├── __init__.py
├── main.py                     # FastAPI app factory
├── dependencies.py             # Dependency injection
├── middleware/
│   ├── __init__.py
│   ├── error_handler.py        # Global error handling
│   ├── request_id.py           # Request ID tracking
│   └── rate_limiter.py         # API rate limiting
├── routes/
│   ├── __init__.py
│   ├── documents.py            # /api/v1/documents
│   ├── analysis.py             # /api/v1/analysis
│   ├── feedback.py             # /api/v1/feedback
│   ├── policies.py             # /api/v1/policies
│   ├── audit.py                # /api/v1/audit
│   └── health.py               # /api/v1/health
└── schemas/
    ├── __init__.py
    ├── documents.py            # Document DTOs
    ├── analysis.py             # Analysis DTOs
    ├── feedback.py             # Feedback DTOs
    ├── policies.py             # Policy DTOs
    └── common.py               # Shared schemas (pagination, errors)
```

### 5.2 Dependency Injection

```python
# src/api/dependencies.py
from functools import lru_cache

class Container:
    def __init__(self, settings: Settings):
        self._settings = settings
        self._event_store = None
        self._repositories = {}
    
    @property
    def event_store(self) -> EventStore:
        if self._event_store is None:
            self._event_store = PostgresEventStore(self._settings.database_url)
        return self._event_store
    
    @property
    def document_repository(self) -> DocumentRepository:
        return DocumentRepository(self.event_store, self.snapshot_store)
    
    # ... other dependencies

@lru_cache
def get_container() -> Container:
    return Container(get_settings())

def get_upload_handler(container: Container = Depends(get_container)):
    return UploadDocumentHandler(
        container.document_repository,
        container.converter_factory,
        container.event_publisher
    )
```

### 5.3 Route Implementation

```python
# src/api/routes/documents.py
from fastapi import APIRouter, Depends, UploadFile, File

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

@router.post("/", response_model=DocumentResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    policy_repository_id: Optional[UUID] = None,
    handler: UploadDocumentHandler = Depends(get_upload_handler)
) -> DocumentResponse:
    command = UploadDocument(
        filename=file.filename,
        content=await file.read(),
        content_type=file.content_type,
        uploaded_by="anonymous",  # TODO: Get from auth
        policy_repository_id=policy_repository_id
    )
    document_id = await handler.handle(command)
    return DocumentResponse(id=document_id)

@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: UUID,
    queries: DocumentQueries = Depends(get_document_queries)
) -> DocumentDetailResponse:
    document = await queries.get_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDetailResponse.from_view(document)
```

---

## Phase 6: Frontend Implementation

**Duration**: 4-5 weeks  
**Goal**: Build complete React frontend with document management, issue blotter, AI chatbot, and parameter visualization

### 6.1 Phase Overview

The frontend implementation is divided into 6 increments:
1. **Foundation Setup** - Routing, API client, state management
2. **Document Upload Page** - File upload with validation
3. **Document List Page** - Paginated document browser
4. **Document Detail Page** - Core layout with tabbed interface
5. **AI Chatbot Integration** - Interactive issue exploration
6. **Parameter Graph Visualization** - Dependency diagram

### 6.2 Dependencies to Install

```bash
cd client
npm install react-router-dom @tanstack/react-query axios @xyflow/react
npm install -D @types/react-router-dom
```

### 6.3 Project Structure

**Files to Create**:
```
client/src/
├── lib/
│   ├── api.ts                  # Axios instance with base URL
│   └── utils.ts                # Utility functions (existing)
├── types/
│   ├── index.ts                # Re-exports
│   ├── document.ts             # Document, DocumentStatus DTOs
│   ├── analysis.ts             # AnalysisSession, AnalysisResult DTOs
│   ├── feedback.ts             # FeedbackItem, Severity, AcceptanceStatus
│   ├── chat.ts                 # ChatMessage, ChatRequest, ChatResponse
│   └── graph.ts                # GraphNode, GraphEdge, ParameterDependency
├── services/
│   ├── documents.ts            # Document CRUD operations
│   ├── analysis.ts             # Analysis start/status/results
│   ├── feedback.ts             # Accept/reject feedback items
│   ├── chat.ts                 # AI chat interactions
│   └── parameters.ts           # Parameter graph data
├── hooks/
│   ├── useDocuments.ts         # Document list/detail queries
│   ├── useDocument.ts          # Single document query
│   ├── useUploadDocument.ts    # Upload mutation
│   ├── useAnalysis.ts          # Analysis queries/mutations
│   ├── useFeedback.ts          # Feedback queries/mutations
│   ├── useChat.ts              # Chat message management
│   └── useParameters.ts        # Parameter graph data
├── components/
│   ├── ui/                     # Shadcn/ui components
│   │   ├── button.tsx          # (existing)
│   │   ├── card.tsx            # (existing)
│   │   ├── table.tsx           # NEW: Data tables
│   │   ├── tabs.tsx            # NEW: Tabbed interface
│   │   ├── badge.tsx           # NEW: Status badges
│   │   ├── dialog.tsx          # NEW: Modal dialogs
│   │   ├── input.tsx           # NEW: Form inputs
│   │   ├── textarea.tsx        # NEW: Chat input
│   │   ├── scroll-area.tsx     # NEW: Scrollable containers
│   │   ├── skeleton.tsx        # NEW: Loading states
│   │   ├── tooltip.tsx         # NEW: Tooltips
│   │   └── alert.tsx           # NEW: Error/success messages
│   ├── layout/
│   │   ├── Header.tsx          # Navigation header
│   │   ├── Layout.tsx          # Page wrapper with header
│   │   └── ErrorBoundary.tsx   # Error handling
│   ├── documents/
│   │   ├── DocumentUploadForm.tsx    # Upload form with drag-drop
│   │   ├── DocumentCard.tsx          # Document preview card
│   │   ├── DocumentTable.tsx         # Document list table
│   │   ├── DocumentStatusBadge.tsx   # Status indicator
│   │   └── PolicySelector.tsx        # Policy repository picker
│   ├── analysis/
│   │   ├── AnalysisProgress.tsx      # Analysis status/progress
│   │   ├── AnalysisTrigger.tsx       # Start analysis button
│   │   └── AnalysisSummary.tsx       # Results overview
│   ├── feedback/
│   │   ├── IssueBlotter.tsx          # Main issue list component
│   │   ├── IssueRow.tsx              # Expandable issue row
│   │   ├── IssueDetails.tsx          # Issue detail panel
│   │   ├── SeverityBadge.tsx         # Severity indicator
│   │   ├── AcceptRejectButtons.tsx   # Action buttons
│   │   └── DiffViewer.tsx            # Before/after comparison
│   ├── chat/
│   │   ├── ChatPanel.tsx             # Main chat container
│   │   ├── ChatMessageList.tsx       # Message history
│   │   ├── ChatMessage.tsx           # Single message bubble
│   │   ├── ChatComposer.tsx          # Message input
│   │   └── TypingIndicator.tsx       # AI typing animation
│   └── graph/
│       ├── ParameterGraph.tsx        # React Flow graph wrapper
│       ├── ParameterNode.tsx         # Custom node component
│       ├── DependencyEdge.tsx        # Custom edge component
│       └── GraphControls.tsx         # Zoom/pan controls
├── pages/
│   ├── HomePage.tsx                  # Landing page (existing App.tsx content)
│   ├── DocumentsPage.tsx             # Document list
│   ├── DocumentUploadPage.tsx        # Upload new document
│   ├── DocumentDetailPage.tsx        # Detail with tabs
│   ├── PoliciesPage.tsx              # Policy management (future)
│   └── AuditLogPage.tsx              # Audit trail (future)
├── App.tsx                           # Router setup
└── main.tsx                          # App entry point
```

---

### 6.4 Increment 1: Foundation Setup

**Duration**: 3-4 days

#### 6.4.1 API Client Setup

```typescript
// client/src/lib/api.ts
import axios from 'axios';

export const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request/response interceptors for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle common errors (401, 500, etc.)
    return Promise.reject(error);
  }
);
```

#### 6.4.2 TypeScript DTOs

```typescript
// client/src/types/document.ts
export interface Document {
  id: string;
  filename: string;
  originalFormat: string;
  status: DocumentStatus;
  version: string;
  policyRepositoryId?: string;
  createdAt: string;
  updatedAt: string;
}

export type DocumentStatus = 
  | 'uploaded' 
  | 'converting' 
  | 'converted' 
  | 'analyzing' 
  | 'analyzed' 
  | 'error';

// client/src/types/feedback.ts
export interface FeedbackItem {
  id: string;
  documentId: string;
  sectionId?: string;
  issueType: string;
  severity: 'critical' | 'major' | 'minor' | 'suggestion';
  description: string;
  originalText?: string;
  suggestedText?: string;
  policyReference?: string;
  status: 'pending' | 'accepted' | 'rejected' | 'modified';
  confidence: number;
  createdAt: string;
}

// client/src/types/chat.ts
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  timestamp: string;
}

export interface Citation {
  feedbackId: string;
  sectionTitle: string;
}

// client/src/types/graph.ts
export interface ParameterNode {
  id: string;
  name: string;
  definition: string;
  type: 'parameter' | 'term' | 'formula';
}

export interface ParameterEdge {
  source: string;
  target: string;
  relationship: 'uses' | 'defines' | 'references';
}
```

#### 6.4.3 React Router Setup

```typescript
// client/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/layout/Layout';
import { HomePage } from './pages/HomePage';
import { DocumentsPage } from './pages/DocumentsPage';
import { DocumentUploadPage } from './pages/DocumentUploadPage';
import { DocumentDetailPage } from './pages/DocumentDetailPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<HomePage />} />
            <Route path="documents" element={<DocumentsPage />} />
            <Route path="documents/upload" element={<DocumentUploadPage />} />
            <Route path="documents/:id" element={<DocumentDetailPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

---

### 6.5 Increment 2: Document Upload Page

**Duration**: 2-3 days

#### Features:
- Drag-and-drop file upload
- Supported formats: PDF, DOCX, MD, RST
- File size validation (max 100 pages / 10MB)
- Policy repository selection
- Upload progress indicator
- Success redirect to document detail

#### Key Component:

```typescript
// client/src/components/documents/DocumentUploadForm.tsx
export function DocumentUploadForm() {
  const navigate = useNavigate();
  const { mutate: upload, isPending, error } = useUploadDocument();
  const [dragActive, setDragActive] = useState(false);
  
  const onDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer?.files || []);
    const validFile = files.find(f => isValidFormat(f));
    
    if (validFile) {
      upload(
        { file: validFile, policyRepositoryId: selectedPolicy },
        {
          onSuccess: (data) => navigate(`/documents/${data.id}`),
        }
      );
    }
  }, [upload, selectedPolicy, navigate]);
  
  return (
    <div 
      className={cn(
        "border-2 border-dashed rounded-lg p-12 text-center",
        dragActive && "border-primary bg-primary/5"
      )}
      onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
      onDragLeave={() => setDragActive(false)}
      onDrop={onDrop}
    >
      {isPending ? (
        <UploadProgress />
      ) : (
        <>
          <Upload className="mx-auto h-12 w-12 text-muted-foreground" />
          <p>Drag & drop your document here, or click to browse</p>
          <p className="text-sm text-muted-foreground">
            Supports PDF, Word, Markdown, and RST (max 10MB)
          </p>
        </>
      )}
    </div>
  );
}
```

---

### 6.6 Increment 3: Document List Page

**Duration**: 2-3 days

#### Features:
- Paginated table with sorting
- Status badges with color coding
- Search/filter functionality
- Quick actions (view, delete, re-analyze)
- Empty state for new users
- Loading skeletons

#### Key Component:

```typescript
// client/src/pages/DocumentsPage.tsx
export function DocumentsPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const { data, isLoading, error } = useDocuments({ page, search });
  
  if (isLoading) return <DocumentTableSkeleton />;
  if (error) return <ErrorAlert message="Failed to load documents" />;
  if (!data?.documents.length) return <EmptyDocumentState />;
  
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Your Documents</h1>
        <Button asChild>
          <Link to="/documents/upload">
            <Upload className="mr-2 h-4 w-4" /> Upload Document
          </Link>
        </Button>
      </div>
      
      <SearchInput value={search} onChange={setSearch} />
      
      <DocumentTable 
        documents={data.documents}
        onRowClick={(doc) => navigate(`/documents/${doc.id}`)}
      />
      
      <Pagination 
        currentPage={page}
        totalPages={data.totalPages}
        onPageChange={setPage}
      />
    </div>
  );
}
```

---

### 6.7 Increment 4: Document Detail Page with Issue Blotter

**Duration**: 4-5 days

#### Features:
- Document metadata panel (status, version, policy, dates)
- Tabbed interface: Issues | Chat | Parameters
- **Issue Blotter Tab**:
  - Table of all feedback items
  - Grouped by severity (critical, major, minor, suggestion)
  - Expandable rows with full issue details
  - Accept/Reject/Modify actions
  - Optimistic updates on actions
  - Issue counts by status

#### Key Components:

```typescript
// client/src/pages/DocumentDetailPage.tsx
export function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: document, isLoading } = useDocument(id!);
  const { data: feedback } = useFeedback(id!);
  
  if (isLoading) return <DocumentDetailSkeleton />;
  if (!document) return <NotFound />;
  
  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Left Panel - Metadata */}
      <div className="col-span-3">
        <DocumentMetadataPanel document={document} />
        <AnalysisTrigger documentId={id!} status={document.status} />
      </div>
      
      {/* Right Panel - Tabbed Content */}
      <div className="col-span-9">
        <Tabs defaultValue="issues">
          <TabsList>
            <TabsTrigger value="issues">
              Issues <Badge variant="secondary">{feedback?.length || 0}</Badge>
            </TabsTrigger>
            <TabsTrigger value="chat">AI Assistant</TabsTrigger>
            <TabsTrigger value="graph">Parameters</TabsTrigger>
          </TabsList>
          
          <TabsContent value="issues">
            <IssueBlotter documentId={id!} feedback={feedback || []} />
          </TabsContent>
          
          <TabsContent value="chat">
            <ChatPanel documentId={id!} feedback={feedback || []} />
          </TabsContent>
          
          <TabsContent value="graph">
            <ParameterGraph documentId={id!} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

// client/src/components/feedback/IssueBlotter.tsx
export function IssueBlotter({ documentId, feedback }: IssueBlotterProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const { mutate: acceptFeedback } = useAcceptFeedback();
  const { mutate: rejectFeedback } = useRejectFeedback();
  
  const grouped = useMemo(() => groupBySeverity(feedback), [feedback]);
  const counts = useMemo(() => countByStatus(feedback), [feedback]);
  
  return (
    <div className="space-y-4">
      {/* Summary Stats */}
      <div className="flex gap-4">
        <StatCard label="Pending" value={counts.pending} variant="warning" />
        <StatCard label="Accepted" value={counts.accepted} variant="success" />
        <StatCard label="Rejected" value={counts.rejected} variant="muted" />
      </div>
      
      {/* Issue Table */}
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Severity</TableHead>
            <TableHead>Issue Type</TableHead>
            <TableHead>Description</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {feedback.map((item) => (
            <IssueRow
              key={item.id}
              issue={item}
              isExpanded={expandedId === item.id}
              onToggle={() => setExpandedId(
                expandedId === item.id ? null : item.id
              )}
              onAccept={() => acceptFeedback({ documentId, feedbackId: item.id })}
              onReject={() => rejectFeedback({ documentId, feedbackId: item.id })}
            />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

---

### 6.8 Increment 5: AI Chatbot Integration

**Duration**: 3-4 days

#### Features:
- Chat panel with message history
- User input composer with send button
- AI typing indicator during response
- Context-aware responses about document issues
- Clickable citations linking to specific issues
- Message persistence within session

#### Backend Requirements:
**NEW ENDPOINT NEEDED**: `POST /api/v1/documents/{id}/chat`
```json
Request:  { "message": "string", "context": { "feedbackIds": ["uuid"] } }
Response: { "reply": "string", "citations": [{ "feedbackId": "uuid", "excerpt": "string" }] }
```

#### Key Components:

```typescript
// client/src/components/chat/ChatPanel.tsx
export function ChatPanel({ documentId, feedback }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const { mutate: sendMessage, isPending } = useSendChatMessage();
  const scrollRef = useRef<HTMLDivElement>(null);
  
  const handleSend = (content: string) => {
    // Add user message immediately
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    
    // Send to API
    sendMessage(
      { documentId, message: content, feedbackIds: feedback.map(f => f.id) },
      {
        onSuccess: (response) => {
          setMessages(prev => [...prev, {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: response.reply,
            citations: response.citations,
            timestamp: new Date().toISOString(),
          }]);
        },
      }
    );
  };
  
  return (
    <div className="flex flex-col h-[600px] border rounded-lg">
      {/* Message List */}
      <ScrollArea ref={scrollRef} className="flex-1 p-4">
        <ChatMessageList messages={messages} />
        {isPending && <TypingIndicator />}
      </ScrollArea>
      
      {/* Composer */}
      <ChatComposer onSend={handleSend} disabled={isPending} />
    </div>
  );
}

// client/src/components/chat/ChatMessage.tsx
export function ChatMessage({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  
  return (
    <div className={cn(
      "flex gap-3 mb-4",
      isUser ? "justify-end" : "justify-start"
    )}>
      {!isUser && <BotAvatar />}
      <div className={cn(
        "max-w-[80%] rounded-lg px-4 py-2",
        isUser ? "bg-primary text-primary-foreground" : "bg-muted"
      )}>
        <p>{message.content}</p>
        {message.citations?.length > 0 && (
          <div className="mt-2 text-xs opacity-80">
            <span>References: </span>
            {message.citations.map((c, i) => (
              <CitationLink key={i} citation={c} />
            ))}
          </div>
        )}
      </div>
      {isUser && <UserAvatar />}
    </div>
  );
}
```

---

### 6.9 Increment 6: Parameter Graph Visualization

**Duration**: 3-4 days

#### Features:
- Interactive node-edge graph using React Flow
- Parameter nodes showing name and definition
- Directed edges showing usage relationships
- Zoom and pan controls
- Node click to highlight dependencies
- Minimap for navigation
- Export graph as image

#### Backend Requirements:
**NEW ENDPOINT NEEDED**: `GET /api/v1/documents/{id}/parameters`
```json
Response: {
  "nodes": [
    { "id": "uuid", "name": "string", "definition": "string", "type": "parameter|term|formula" }
  ],
  "edges": [
    { "source": "uuid", "target": "uuid", "relationship": "uses|defines|references" }
  ]
}
```

#### Key Components:

```typescript
// client/src/components/graph/ParameterGraph.tsx
import { 
  ReactFlow, 
  Background, 
  Controls, 
  MiniMap,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

export function ParameterGraph({ documentId }: { documentId: string }) {
  const { data, isLoading, error } = useParameters(documentId);
  
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  
  useEffect(() => {
    if (data) {
      setNodes(data.nodes.map(n => ({
        id: n.id,
        type: 'parameter',
        position: calculatePosition(n, data.nodes), // Auto-layout
        data: { label: n.name, definition: n.definition, type: n.type },
      })));
      
      setEdges(data.edges.map(e => ({
        id: `${e.source}-${e.target}`,
        source: e.source,
        target: e.target,
        type: 'dependency',
        animated: e.relationship === 'uses',
        label: e.relationship,
      })));
    }
  }, [data]);
  
  if (isLoading) return <GraphSkeleton />;
  if (error) return <ErrorAlert message="Failed to load parameter graph" />;
  if (!data?.nodes.length) return <EmptyGraphState />;
  
  return (
    <div className="h-[600px] border rounded-lg">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={{ parameter: ParameterNode }}
        edgeTypes={{ dependency: DependencyEdge }}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}

// client/src/components/graph/ParameterNode.tsx
export function ParameterNode({ data }: NodeProps) {
  const colorMap = {
    parameter: 'bg-blue-100 border-blue-400',
    term: 'bg-green-100 border-green-400',
    formula: 'bg-purple-100 border-purple-400',
  };
  
  return (
    <div className={cn(
      "px-4 py-2 rounded-lg border-2 shadow-sm",
      colorMap[data.type]
    )}>
      <Tooltip content={data.definition}>
        <div className="font-medium">{data.label}</div>
      </Tooltip>
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
}
```

---

### 6.10 Backend API Extensions Required

The frontend requires two new backend endpoints:

#### 1. Chat Endpoint
**File**: `src/api/routes/chat.py`
```python
@router.post("/documents/{document_id}/chat")
async def chat_with_document(
    document_id: UUID,
    request: ChatRequest,
    ai_service: AIService = Depends(get_ai_service)
) -> ChatResponse:
    """Query AI about document issues"""
    pass
```

#### 2. Parameters Endpoint
**File**: `src/api/routes/documents.py` (extend)
```python
@router.get("/documents/{document_id}/parameters")
async def get_document_parameters(
    document_id: UUID,
    queries: DocumentQueries = Depends(get_document_queries)
) -> ParameterGraphResponse:
    """Get parameter dependency graph for document"""
    pass
```

---

### 6.11 Additional Shadcn/ui Components Needed

Install via npx shadcn-ui:
```bash
cd client
npx shadcn@latest add table tabs badge dialog input textarea scroll-area skeleton tooltip alert separator avatar dropdown-menu
```

---

### 6.12 Testing Strategy

| Component | Test Type | Coverage |
|-----------|-----------|----------|
| API Services | Unit (Vitest) | Request/response handling |
| Hooks | Unit (React Testing Library) | State management, mutations |
| Pages | Integration | User flows, navigation |
| Issue Blotter | Component | Expand/collapse, actions |
| Chat Panel | Component | Message flow, loading states |
| Parameter Graph | Component | Node rendering, interactions |

---

## Phase 7: Test Infrastructure

**Duration**: Ongoing (parallel to development)  
**Goal**: Comprehensive test coverage following best practices

### 7.1 Test Structure

```
tests/
├── conftest.py                 # Shared fixtures
├── unit/
│   ├── domain/
│   │   ├── test_value_objects.py
│   │   ├── test_events.py
│   │   ├── test_aggregates.py
│   │   └── test_domain_services.py
│   ├── application/
│   │   ├── test_command_handlers.py
│   │   └── test_query_handlers.py
│   └── infrastructure/
│       ├── test_converters.py
│       └── test_projections.py
├── integration/
│   ├── test_event_store.py
│   ├── test_repositories.py
│   ├── test_projections.py
│   └── test_api_endpoints.py
├── e2e/
│   ├── test_document_workflow.py
│   ├── test_analysis_workflow.py
│   └── test_feedback_workflow.py
└── fixtures/
    ├── documents/              # Sample documents for testing
    ├── events/                 # Event fixtures
    └── factories.py            # Test data factories
```

### 7.2 Testing Strategy

**Layer-by-Layer Approach**:

| Layer | Test Type | Focus | Tools |
|-------|-----------|-------|-------|
| Domain | Unit | Business rules, invariants | pytest, hypothesis |
| Application | Unit + Integration | Command/query handling | pytest, async mocks |
| Infrastructure | Integration | Database, external services | pytest, testcontainers |
| API | Integration | HTTP contracts | pytest, httpx |
| Frontend | Unit + E2E | Components, user flows | vitest, playwright |

### 7.3 Domain Layer Tests

Test aggregates in isolation:
```python
# tests/unit/domain/test_aggregates.py
import pytest
from uuid import uuid4
from src.domain.aggregates.document import Document
from src.domain.events import DocumentUploaded, DocumentConverted

class TestDocumentAggregate:
    def test_upload_creates_document_with_uploaded_event(self):
        doc_id = uuid4()
        
        document = Document.upload(
            document_id=doc_id,
            filename="test.pdf",
            content=b"test content",
            original_format="application/pdf",
            uploaded_by="user@example.com"
        )
        
        assert document.id == doc_id
        assert len(document.pending_events) == 1
        assert isinstance(document.pending_events[0], DocumentUploaded)
    
    def test_convert_adds_converted_event(self):
        document = self._create_uploaded_document()
        
        document.convert(
            markdown_content="# Test",
            sections=[{"title": "Test", "content": "content"}],
            metadata={"page_count": 1}
        )
        
        assert len(document.pending_events) == 2
        assert isinstance(document.pending_events[1], DocumentConverted)
    
    def test_reconstitute_rebuilds_from_events(self):
        events = [
            DocumentUploaded(
                aggregate_id=uuid4(),
                filename="test.pdf",
                original_format="application/pdf",
                file_size_bytes=100,
                uploaded_by="user@example.com"
            ),
            DocumentConverted(
                aggregate_id=uuid4(),
                markdown_content="# Test",
                sections=[],
                metadata={}
            )
        ]
        
        document = Document.reconstitute(events)
        
        assert document.version == 2
        assert document.status == DocumentStatus.CONVERTED
```

### 7.4 Integration Tests

Test with real database:
```python
# tests/integration/test_event_store.py
import pytest
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:15") as container:
        yield container

@pytest.fixture
async def event_store(postgres):
    pool = await asyncpg.create_pool(postgres.get_connection_url())
    await run_migrations(pool)
    store = PostgresEventStore(pool)
    yield store
    await pool.close()

class TestEventStore:
    async def test_append_and_retrieve_events(self, event_store):
        aggregate_id = uuid4()
        events = [
            DocumentUploaded(aggregate_id=aggregate_id, filename="test.pdf", ...)
        ]
        
        await event_store.append(aggregate_id, events, expected_version=0)
        retrieved = await event_store.get_events(aggregate_id)
        
        assert len(retrieved) == 1
        assert retrieved[0].event_type == "DocumentUploaded"
    
    async def test_optimistic_concurrency_check(self, event_store):
        aggregate_id = uuid4()
        events = [DocumentUploaded(...)]
        
        await event_store.append(aggregate_id, events, expected_version=0)
        
        with pytest.raises(ConcurrencyError):
            await event_store.append(aggregate_id, events, expected_version=0)
```

### 7.5 API Tests

Test HTTP contracts:
```python
# tests/integration/test_api_endpoints.py
import pytest
from httpx import AsyncClient
from src.api.main import create_app

@pytest.fixture
async def client():
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

class TestDocumentEndpoints:
    async def test_upload_document_returns_201(self, client):
        with open("tests/fixtures/documents/sample.pdf", "rb") as f:
            response = await client.post(
                "/api/v1/documents/",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )
        
        assert response.status_code == 201
        assert "id" in response.json()
    
    async def test_get_nonexistent_document_returns_404(self, client):
        response = await client.get(f"/api/v1/documents/{uuid4()}")
        
        assert response.status_code == 404
```

### 7.6 Frontend Tests

Component tests with Vitest:
```typescript
// client/src/components/documents/__tests__/DocumentUpload.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { DocumentUpload } from '../DocumentUpload';

describe('DocumentUpload', () => {
  it('shows drag zone when no file is selected', () => {
    render(<DocumentUpload />);
    
    expect(screen.getByText(/drag and drop/i)).toBeInTheDocument();
  });
  
  it('calls upload mutation when file is dropped', async () => {
    const uploadMock = vi.fn();
    vi.mock('../../../hooks/useDocuments', () => ({
      useUploadDocument: () => ({ mutate: uploadMock, isPending: false })
    }));
    
    render(<DocumentUpload />);
    
    const dropZone = screen.getByTestId('drop-zone');
    const file = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    
    fireEvent.drop(dropZone, { dataTransfer: { files: [file] } });
    
    expect(uploadMock).toHaveBeenCalledWith(expect.objectContaining({
      file: expect.any(File)
    }));
  });
});
```

E2E tests with Playwright:
```typescript
// e2e/document-workflow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Document Workflow', () => {
  test('user can upload document and receive analysis', async ({ page }) => {
    await page.goto('/');
    
    // Upload document
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles('fixtures/sample-algorithm.pdf');
    
    // Wait for upload completion
    await expect(page.getByText('Document uploaded')).toBeVisible();
    
    // Start analysis
    await page.click('button:has-text("Analyze")');
    
    // Wait for analysis (may take time)
    await expect(page.getByText('Analysis complete')).toBeVisible({ timeout: 180000 });
    
    // Verify suggestions appear
    await expect(page.getByTestId('suggestion-card')).toHaveCount({ min: 1 });
  });
});
```

### 7.7 Test Data Factories

```python
# tests/fixtures/factories.py
from dataclasses import dataclass
from uuid import uuid4
from faker import Faker

fake = Faker()

class DocumentFactory:
    @staticmethod
    def create(**overrides):
        defaults = {
            "id": uuid4(),
            "filename": fake.file_name(extension="pdf"),
            "original_format": "application/pdf",
            "uploaded_by": fake.email(),
            "markdown_content": fake.text(max_nb_chars=1000),
        }
        return {**defaults, **overrides}
    
    @staticmethod
    def create_events(document_id=None):
        doc_id = document_id or uuid4()
        return [
            DocumentUploaded(
                aggregate_id=doc_id,
                filename="test.pdf",
                original_format="application/pdf",
                file_size_bytes=1024,
                uploaded_by="test@example.com"
            )
        ]
```

---

## Phase 8: Production Hardening

**Duration**: 2 weeks  
**Goal**: Prepare for production deployment

### 8.1 Security

**Implementation Checklist**:
- [ ] JWT authentication with refresh tokens
- [ ] Role-based access control (RBAC)
- [ ] Input validation and sanitization
- [ ] Rate limiting per endpoint
- [ ] CORS configuration
- [ ] Security headers (CSP, HSTS, etc.)
- [ ] Secrets management (environment variables)
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (output encoding)
- [ ] CSRF protection

### 8.2 Observability

**Files to Create**:
```
src/infrastructure/observability/
├── __init__.py
├── logging.py              # Structured logging setup
├── metrics.py              # Prometheus metrics
├── tracing.py              # Distributed tracing
└── health.py               # Health check endpoints
```

**Structured Logging**:
```python
import structlog

def configure_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
```

### 8.3 Performance

**Optimizations**:
- [ ] Database connection pooling
- [ ] Query optimization with indexes
- [ ] Caching layer (Redis) for read models
- [ ] Async I/O throughout
- [ ] Pagination for all list endpoints
- [ ] Aggregate snapshots for performance
- [ ] Background job processing for analysis

### 8.4 Resilience

**Implementation**:
- [ ] Circuit breakers for AI providers
- [ ] Retry logic with exponential backoff
- [ ] Graceful degradation
- [ ] Health checks for dependencies
- [ ] Database migration strategy

### 8.5 Documentation

**Production Documentation**:
```
docs/
├── deployment/
│   ├── DEPLOYMENT_GUIDE.md
│   ├── ENVIRONMENT_VARIABLES.md
│   └── RUNBOOK.md
├── api/
│   └── openapi.yaml        # Already exists
└── operations/
    ├── MONITORING.md
    └── TROUBLESHOOTING.md
```

---

## Implementation Timeline

### Summary

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Domain Layer | 2-3 weeks | None |
| Phase 2: Infrastructure Layer | 2-3 weeks | Phase 1 |
| Phase 3: Application Layer | 2-3 weeks | Phase 1, 2 |
| Phase 4: AI Integration | 2-3 weeks | Phase 1, 2 |
| Phase 5: API Layer | 2 weeks | Phase 3 |
| Phase 6: Frontend | 3-4 weeks | Phase 5 |
| Phase 7: Testing | Ongoing | All phases |
| Phase 8: Production Hardening | 2 weeks | All phases |

**Total Estimated Duration**: 16-22 weeks

### Parallel Work Streams

```
Week 1-3:   [Domain Layer] ─────────────────────────┐
Week 4-6:   [Infrastructure Layer] ────────────────┐│
Week 7-9:   [Application Layer] ──────────────────┐││
Week 7-9:   [AI Integration] ─────────────────────┼┤│
Week 10-11: [API Layer] ──────────────────────────┤││
Week 12-15: [Frontend] ───────────────────────────┤││
Week 1-15:  [Testing] ────────────────────────────┘┘┘
Week 16-18: [Production Hardening] ────────────────────
```

---

## Quality Gates

### Per-Phase Completion Criteria

**Phase 1 - Domain Layer**:
- [ ] All value objects immutable with validation
- [ ] All events follow naming conventions
- [ ] All aggregates enforce invariants
- [ ] 90%+ unit test coverage
- [ ] Domain model review completed

**Phase 2 - Infrastructure Layer**:
- [ ] Event store passes concurrency tests
- [ ] Projections handle all event types
- [ ] Database migrations versioned
- [ ] Integration tests pass

**Phase 3 - Application Layer**:
- [ ] All commands have handlers
- [ ] All queries have handlers
- [ ] Unit of work manages transactions
- [ ] Handler tests pass

**Phase 4 - AI Integration**:
- [ ] All providers implement interface
- [ ] Rate limiting in place
- [ ] Fallback behavior tested
- [ ] Cost estimation available

**Phase 5 - API Layer**:
- [ ] All OpenAPI endpoints implemented
- [ ] Request validation complete
- [ ] Error responses consistent
- [ ] API tests pass

**Phase 6 - Frontend**:
- [ ] All user flows implemented
- [ ] Responsive design verified
- [ ] Accessibility audit passed
- [ ] E2E tests pass

**Phase 7 - Testing**:
- [ ] 80%+ overall code coverage
- [ ] All critical paths have E2E tests
- [ ] Performance benchmarks met
- [ ] Security scan passed

**Phase 8 - Production**:
- [ ] Security checklist completed
- [ ] Monitoring configured
- [ ] Runbook documented
- [ ] Load testing passed

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| AI provider rate limits | Implement queuing and backpressure |
| Long-running analysis timeout | Use background jobs with progress tracking |
| Event store performance | Implement snapshots at version thresholds |
| Schema evolution | Use event upcasting and versioning |
| Security vulnerabilities | Regular dependency audits, pen testing |

---

## Next Steps

1. **Immediate**: Begin Phase 1 (Domain Layer) implementation
2. **Set up**: CI/CD pipeline with automated testing
3. **Configure**: Development and staging environments
4. **Document**: API changes in OpenAPI spec as developed

---

## Future Phases

### Phase 9: Document Group Support (Multi-Document Analysis)

**Duration**: 2-3 weeks  
**Goal**: Enable analysis of multiple related documents together for comprehensive self-containment validation

**Reference**: [ADR-010: Document Group for Multi-Document Analysis](decisions/010-document-group-multi-document-analysis.md)

#### 9.1 Domain Layer Extensions

**Files to Create**:
```
src/domain/aggregates/document_group.py      # DocumentGroup aggregate
src/domain/events/document_group_events.py   # Group-related events
src/domain/commands/document_group_commands.py # Group commands
src/domain/value_objects/group_status.py     # Group completeness status
```

**Domain Events**:
- `DocumentGroupCreated` - Group initialized
- `DocumentAddedToGroup` - Document assigned to group
- `DocumentRemovedFromGroup` - Document removed from group
- `PrimaryDocumentSet` - Main document designated
- `GroupAnalysisStarted` - Combined analysis initiated
- `GroupAnalysisCompleted` - Analysis results available
- `GroupCompletenessChanged` - Status updated based on reference validation

**Commands**:
- `CreateDocumentGroup` - Create a new group
- `AddDocumentToGroup` - Assign document to group
- `RemoveDocumentFromGroup` - Remove document from group
- `SetPrimaryDocument` - Designate main document
- `AnalyzeDocumentGroup` - Trigger combined analysis

#### 9.2 Infrastructure Layer Extensions

**Files to Create**:
```
src/infrastructure/repositories/document_group_repository.py
src/infrastructure/projections/document_group_projector.py
src/infrastructure/queries/document_group_queries.py
```

**Combined Content Preparation**:
```python
def prepare_group_content(group: DocumentGroup, documents: List[Document]) -> str:
    """Concatenate documents with clear separators for AI analysis."""
    parts = []
    for doc in documents:
        is_primary = doc.id == group.primary_document_id
        header = f"=== DOCUMENT: {doc.filename}"
        if is_primary:
            header += " (PRIMARY)"
        header += " ==="
        parts.append(f"{header}\n\n{doc.markdown_content}")
    return "\n\n".join(parts)
```

#### 9.3 Application Layer Extensions

**Files to Create**:
```
src/application/commands/document_group_handlers.py
src/application/queries/document_group_queries.py
```

#### 9.4 API Layer Extensions

**New Endpoints**:
```
POST   /api/v1/document-groups                    Create group
GET    /api/v1/document-groups                    List groups
GET    /api/v1/document-groups/{id}               Get group details
PUT    /api/v1/document-groups/{id}               Update group metadata
DELETE /api/v1/document-groups/{id}               Delete group

POST   /api/v1/document-groups/{id}/documents     Add document to group
DELETE /api/v1/document-groups/{id}/documents/{docId}  Remove document
PUT    /api/v1/document-groups/{id}/primary       Set primary document

POST   /api/v1/document-groups/{id}/analyze       Start group analysis
GET    /api/v1/document-groups/{id}/analysis      Get analysis results
```

**Files to Create**:
```
src/api/routes/document_groups.py
src/api/schemas/document_groups.py
```

#### 9.5 AI Prompt Updates

Update document analysis prompt to handle multi-document context:
- Recognize document separators in concatenated content
- Track cross-document references
- Validate that references to appendices/attachments resolve within the group
- Produce group-level self-containment score

#### 9.6 Frontend Extensions

**New Pages**:
```
client/src/pages/DocumentGroupsPage.tsx      # List all groups
client/src/pages/DocumentGroupDetailPage.tsx # Group management and analysis
```

**New Components**:
```
client/src/components/DocumentGroupCard.tsx   # Group summary card
client/src/components/GroupDocumentList.tsx   # Documents in group with drag-drop
client/src/components/GroupAnalysisResults.tsx # Combined analysis view
```

**Features**:
- Group creation and management
- Drag-and-drop document assignment
- Visual completeness indicator
- Group analysis trigger and results display

#### 9.7 Completion Criteria

- [ ] DocumentGroup aggregate with event sourcing
- [ ] CRUD API for document groups
- [ ] Document assignment/removal within groups
- [ ] Combined content preparation for AI analysis
- [ ] Cross-document reference validation
- [ ] Group-level self-containment scoring
- [ ] Frontend group management UI
- [ ] E2E tests for group workflows

---

*This plan should be reviewed and updated as implementation progresses. Each phase completion should trigger an update to this document reflecting lessons learned and any scope adjustments.*
