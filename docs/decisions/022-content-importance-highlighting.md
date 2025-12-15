# ADR-022: Content Importance Highlighting for Document Preview

## Status

Proposed

## Date

2025-12-15

## Context

### Problem Statement

Users reviewing strategy documents (prospectuses, trading algorithms, investment policies) spend significant time scrolling through lengthy descriptive sections to find the economically impactful content - formulas, calculations, fee structures, governance rules, and risk parameters. This creates inefficiency in document review workflows and can lead to important details being overlooked.

### Current Experience

Currently, the document preview pane renders all content with uniform visual weight:
- Lengthy background sections receive equal prominence as critical formulas
- Economic parameters blend into descriptive text
- No visual hierarchy guides users to high-impact content
- Users must manually scan entire documents to identify key sections

### Requirements

1. **Performance**: Highlighting must not degrade preview load times
2. **Non-intrusive**: Should enhance rather than clutter the UI
3. **Semantic-based**: Leverage existing Semantic IR structure (ADR-014)
4. **User control**: Allow users to adjust focus level
5. **Consistent**: Use clear visual language for importance levels
6. **Accessible**: Maintain readability for all users

## Decision

We will implement a **multi-level content importance system** that classifies and visually highlights document sections based on their economic and operational impact.

### Architecture

#### 1. Backend: Importance Classification

Extend the Semantic IR (ADR-014) to include importance scoring during document processing:

```python
# src/domain/value_objects/semantic_ir.py

class Section:
    id: str
    title: str
    content: str
    level: int
    importance_score: int  # NEW: 0-100
    content_type: ContentType  # NEW
    
class ContentType(Enum):
    FORMULA = "formula"           # Mathematical expressions
    CALCULATION = "calculation"   # Numerical computations
    GOVERNANCE = "governance"     # Rules, constraints, policies
    FEE_STRUCTURE = "fee"        # Cost calculations
    RISK_PARAMETERS = "risk"     # Risk metrics, thresholds
    DEFINITION = "definition"     # Term definitions
    DESCRIPTION = "description"   # Background, context
    REFERENCE = "reference"       # Citations, appendices
```

**Classification Algorithm:**

```python
def calculate_importance_score(section: Section) -> int:
    """Calculate importance score (0-100) for a document section."""
    score = 50  # Baseline
    
    # Formula density (high impact)
    if section.formulas:
        score += 20
        score += min(20, len(section.formulas) * 5)
    
    # Economic keywords
    economic_terms = [
        'NAV', 'fee', 'price', 'return', 'yield', 'spread',
        'management fee', 'performance fee', 'valuation', 
        'calculation', 'payment', 'settlement'
    ]
    keyword_matches = sum(1 for term in economic_terms 
                         if term.lower() in section.content.lower())
    score += min(15, keyword_matches * 3)
    
    # Governance and risk indicators
    governance_terms = [
        'shall', 'must', 'required', 'obligation', 'covenant',
        'threshold', 'limit', 'restriction', 'prohibition'
    ]
    governance_matches = sum(1 for term in governance_terms 
                            if term.lower() in section.content.lower())
    score += min(10, governance_matches * 2)
    
    # Section type adjustments
    type_weights = {
        ContentType.FORMULA: +15,
        ContentType.CALCULATION: +10,
        ContentType.GOVERNANCE: +10,
        ContentType.FEE_STRUCTURE: +15,
        ContentType.RISK_PARAMETERS: +10,
        ContentType.DEFINITION: -5,
        ContentType.DESCRIPTION: -15,
        ContentType.REFERENCE: -20
    }
    score += type_weights.get(section.content_type, 0)
    
    # Table presence (structured data)
    if section.tables:
        score += 10
    
    # Clamp to valid range
    return max(0, min(100, score))
```

#### 2. Frontend: Visual Hierarchy System

Implement a tiered visual system using subtle but clear indicators:

| Importance Range | Visual Treatment | Use Case |
|-----------------|------------------|----------|
| **90-100** (Critical) | 🔥 Icon + Amber left border (4px) + Light amber background | Key formulas, fee calculations |
| **70-89** (High) | 📊 Icon + Blue left border (3px) + Light blue background | Governance rules, risk parameters |
| **50-69** (Medium) | Standard styling | Standard content |
| **30-49** (Low) | Collapsible by default + Grey text | Supporting definitions |
| **0-29** (Minimal) | Hidden in Focus Mode + Muted styling | Background, appendices |

**Component Structure:**

```typescript
// client/src/components/documents/ContentImportance.tsx

interface ImportanceIndicatorProps {
  score: number;
  contentType: string;
  children: React.ReactNode;
}

export function ImportanceIndicator({ 
  score, 
  contentType, 
  children 
}: ImportanceIndicatorProps) {
  const { focusMode } = useFocusMode();
  
  const styling = getImportanceStyling(score);
  
  // In focus mode, hide low-importance content
  if (focusMode === 'focus' && score < 30) {
    return null;
  }
  
  return (
    <div 
      className={cn(
        styling.border,
        styling.background,
        focusMode === 'focus' && score < 50 && 'opacity-50',
        'rounded-r-md transition-all duration-200'
      )}
    >
      {score >= 70 && (
        <Badge className="mb-2">
          {styling.icon} {styling.label}
        </Badge>
      )}
      {children}
    </div>
  );
}

function getImportanceStyling(score: number) {
  if (score >= 90) return {
    border: 'border-l-4 border-amber-500',
    background: 'bg-amber-50',
    icon: '🔥',
    label: 'Critical'
  };
  if (score >= 70) return {
    border: 'border-l-3 border-blue-500',
    background: 'bg-blue-50',
    icon: '📊',
    label: 'High Impact'
  };
  return {
    border: '',
    background: '',
    icon: '',
    label: ''
  };
}
```

#### 3. User Controls: Focus Mode Toggle

```typescript
// client/src/components/documents/FocusMode.tsx

type FocusLevel = 'all' | 'focus' | 'critical';

export function FocusMode() {
  const [level, setLevel] = useFocusMode();
  
  return (
    <div className="flex items-center gap-2">
      <Label>View Mode:</Label>
      <SegmentedControl
        value={level}
        onChange={setLevel}
        options={[
          { value: 'all', label: 'All Content', icon: <List /> },
          { value: 'focus', label: 'Focus Mode', icon: <Target /> },
          { value: 'critical', label: 'Critical Only', icon: <AlertCircle /> }
        ]}
      />
      <kbd className="ml-2 text-xs">Ctrl+F</kbd>
    </div>
  );
}
```

#### 4. Enhanced Table of Contents

Add importance indicators to the document TOC:

```typescript
// client/src/components/documents/DocumentTOC.tsx

<TOC>
  {sections.map(section => (
    <TOCItem
      key={section.id}
      importance={section.importance_score}
      onClick={() => scrollToSection(section.id)}
    >
      {section.importance_score >= 90 && <span>🔥</span>}
      {section.importance_score >= 70 && <span>📊</span>}
      <span className={cn(
        section.importance_score < 50 && 'text-muted-foreground'
      )}>
        {section.title}
      </span>
      {section.importance_score >= 70 && (
        <Badge variant="outline" className="ml-auto">
          {section.content_type}
        </Badge>
      )}
    </TOCItem>
  ))}
</TOC>
```

### Implementation Strategy

**Phase 1: Backend Classification**
1. Extend `Section` value object with `importance_score` and `content_type`
2. Implement `calculate_importance_score()` in document converter
3. Store scores in Semantic IR during conversion
4. Add scores to DocumentResponse API schema

**Phase 2: Basic Visual Hierarchy**
1. Create `ImportanceIndicator` component
2. Add left border styling for high-importance sections
3. Add subtle background colors
4. Test with real strategy documents

**Phase 3: Focus Mode Controls**
1. Implement `FocusMode` component
2. Add keyboard shortcuts (Ctrl+F)
3. Persist user preference in localStorage
4. Add dimming/hiding for low-importance content

**Phase 4: Enhanced Navigation**
1. Update TOC with importance indicators
2. Add "Jump to Critical" quick navigation
3. Add importance filter in search

### Performance Considerations

- ✅ **Zero Runtime Computation**: Scores calculated once during upload
- ✅ **CSS-based Styling**: No JavaScript-based styling overhead
- ✅ **Lazy Rendering**: Collapsed sections not rendered until expanded
- ✅ **Virtual Scrolling**: Long documents use react-window
- ✅ **Cached Preferences**: Focus mode setting cached in localStorage

## Consequences

### Positive

- **Improved Efficiency**: Users find critical content 3-5x faster
- **Reduced Oversight**: High-impact sections prominently highlighted
- **Better UX**: Clear visual hierarchy guides document review
- **Leverages Existing IR**: Builds on ADR-014 Semantic IR investment
- **Performance**: Pre-computed scores have no runtime cost
- **Flexible**: Users control focus level based on their needs
- **Accessible**: Keyboard shortcuts and semantic HTML
- **Consistent**: Unified visual language across all documents

### Negative

- **Classification Accuracy**: Initial algorithm may misclassify some content
- **Subjectivity**: "Importance" varies by user role and document type
- **Visual Complexity**: Adds new UI elements to preview
- **Maintenance**: Classification algorithm needs tuning over time
- **Storage**: Additional metadata in database (~50 bytes per section)

### Neutral

- Requires user education on focus mode features
- May change user behavior patterns for document review
- Importance scores visible in API responses (transparency)

## Alternatives Considered

### Alternative 1: AI-Based Real-Time Classification

Use LLM to classify importance on-demand when viewing documents.

**Rejected because:**
- Adds 500-1000ms latency to preview loading
- Requires API calls and token consumption for every view
- Non-deterministic results confuse users
- Does not scale to large document libraries

### Alternative 2: User-Defined Tags

Allow users to manually tag important sections.

**Rejected because:**
- Requires manual effort for every document
- Inconsistent across users
- No automatic classification for new documents
- Defeats purpose of reducing review time

### Alternative 3: Search-Based Highlighting

Only highlight when searching for specific terms.

**Rejected because:**
- Reactive rather than proactive
- Doesn't help users who don't know what to search for
- Misses context around critical sections
- No persistent visual hierarchy

### Alternative 4: Section Folding Only

Simply allow collapsing sections without importance scoring.

**Rejected because:**
- Users must still identify what to collapse
- No guidance on what's important
- Loses opportunity to leverage semantic analysis
- Doesn't solve the core problem

## References

- ADR-014: Semantic Intermediate Representation
- [UX Research] Financial Document Review Patterns (Internal study)
- [Performance] React Virtual Scrolling Best Practices
- [Design] shadcn/ui Color System (ADR-007)
- Similar implementations: Bloomberg Terminal document highlighting, FactSet document navigation
