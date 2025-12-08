# ADR-010: Document Group for Multi-Document Analysis

## Status

Proposed

## Date

2025-12-08

## Context

Trading algorithm documentation often consists of multiple related documents that must be analyzed together for comprehensive self-containment validation. Examples include:

1. **Main methodology document** referencing appendices (Appendix A, B, C)
2. **Index calculation document** referencing a corporate actions handling manual
3. **Strategy document** referencing governance frameworks and data service agreements

The current system analyzes documents individually, which means:
- References between documents cannot be validated
- Self-containment checks may incorrectly flag references to documents that ARE included (just in separate files)
- Users must manually ensure all related documents are complete

To properly validate that a document set is truly self-contained for independent implementation, the AI must analyze all related documents together as a single unit.

## Decision

We will implement a **Document Group** aggregate that allows users to:

1. **Create Document Groups** - Named collections of related documents
2. **Assign Documents to Groups** - Add/remove documents from groups
3. **Analyze Groups Together** - Send concatenated content to AI for combined analysis
4. **Track Group Completeness** - Identify which referenced documents are missing from the group

### Domain Model

#### Document Group Aggregate

```
DocumentGroup
├── id: UUID
├── name: string
├── description: string
├── primary_document_id: UUID (main document)
├── member_document_ids: List[UUID]
├── created_at: datetime
├── updated_at: datetime
└── status: pending | complete | incomplete
```

#### New Domain Events

- `DocumentGroupCreated` - Group initialized with name and description
- `DocumentAddedToGroup` - Document assigned to group
- `DocumentRemovedFromGroup` - Document removed from group
- `PrimaryDocumentSet` - Main document designated within the group
- `GroupAnalysisStarted` - Combined analysis initiated
- `GroupAnalysisCompleted` - Analysis results available
- `GroupCompletenessChanged` - Status updated based on reference validation

#### New Commands

- `CreateDocumentGroup` - Create a new group
- `AddDocumentToGroup` - Assign an existing document to a group
- `RemoveDocumentFromGroup` - Remove document from group
- `SetPrimaryDocument` - Designate the main document in the group
- `AnalyzeDocumentGroup` - Trigger combined analysis

### API Endpoints

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

### Analysis Flow

1. User creates a Document Group
2. User uploads documents and assigns them to the group
3. User designates one document as the "primary" (main methodology)
4. User triggers group analysis
5. System concatenates all documents with clear separators:
   ```
   === DOCUMENT: Main_Methodology.md (PRIMARY) ===
   [content]
   
   === DOCUMENT: Appendix_A_Rebalancing.md ===
   [content]
   
   === DOCUMENT: Data_Sources.md ===
   [content]
   ```
6. AI analyzes concatenated content for:
   - Cross-document reference validation
   - Combined self-containment assessment
   - Missing external references (not in group)
7. Results indicate group-level implementability

### Frontend Changes

- New "Document Groups" page listing all groups
- Group detail page showing member documents
- Drag-and-drop interface to add documents to groups
- Visual indicator of group completeness status
- Group analysis trigger and results view

## Consequences

### Positive

- Enables complete self-containment validation for multi-document sets
- Reduces false positives from individual document analysis
- Provides clear visibility into document relationships
- Allows users to build and validate complete documentation packages
- Supports incremental document addition as materials are gathered

### Negative

- Increases complexity of the domain model
- Larger combined documents may increase AI analysis costs
- Users must understand the grouping concept
- Group management adds another layer of organization

### Neutral

- Documents can belong to multiple groups (useful for shared appendices)
- Groups are optional - individual document analysis still supported
- Existing document workflows remain unchanged

## Alternatives Considered

### 1. Automatic Reference Detection

Automatically detect and link documents based on content analysis.

**Not chosen because**: Unreliable for documents with similar names or partial references; users need explicit control over groupings.

### 2. Upload-Time Grouping

Require users to upload all related documents together in a single operation.

**Not chosen because**: Documents are often gathered over time; inflexible for iterative workflows.

### 3. Document Embedding/Attachment

Allow documents to contain other documents as embedded attachments.

**Not chosen because**: Complex document structure; doesn't reflect how documents are typically organized; harder to update individual components.

## Implementation Phases

### Phase 1: Core Group Functionality
- DocumentGroup aggregate and events
- Basic CRUD API endpoints
- Database schema for groups

### Phase 2: Group Analysis
- Combined content preparation
- Updated AI prompts for multi-document context
- Cross-reference validation

### Phase 3: Frontend Integration
- Group management UI
- Document assignment interface
- Group analysis results display

## References

- [ADR-001: DDD with Event Sourcing and CQRS](001-use-ddd-event-sourcing-cqrs.md)
- [ADR-009: Document Self-Containment Requirements](009-document-self-containment-requirements.md)
- Document Analysis Prompt: `src/infrastructure/ai/prompts/document_analysis.py`
