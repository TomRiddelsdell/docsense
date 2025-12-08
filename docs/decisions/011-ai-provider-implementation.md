# ADR-011: AI Provider Implementation with LiteLLM

## Status
Accepted

## Date
2025-12-08

## Context

Following ADR-003's decision to support multiple AI models, we needed to implement the actual AI provider layer. Key challenges encountered:

1. **Google Agent Development Kit (ADK) Compatibility**: Initial attempt to use Google ADK for Gemini revealed version conflicts with other dependencies (pydantic version requirements)
2. **Response Parsing**: AI models return JSON responses wrapped in markdown code blocks, which may be truncated if the response exceeds token limits
3. **Debugging AI Responses**: Without storing AI responses, debugging parsing failures required re-running expensive API calls
4. **Rate Limiting**: Need to manage API rate limits across concurrent requests

## Decision

### 1. LiteLLM as Unified Provider Interface

Instead of implementing separate SDKs for each AI provider, we use **LiteLLM** as a unified interface:

```python
import litellm

response = litellm.completion(
    model="anthropic/claude-sonnet-4-5",
    messages=[...],
    max_tokens=8192,
)
```

**Rationale**: LiteLLM provides a consistent interface for 100+ models with automatic retries, timeout handling, and unified response format.

### 2. Claude Provider as Primary Implementation

The `ClaudeProvider` class implements the `AIProvider` interface using Claude models via LiteLLM:

- **Available Models**: claude-sonnet-4-5, claude-haiku-4-5, claude-opus-4-5
- **Default Model**: claude-sonnet-4-5 (best balance of speed/quality)
- **Request Timeout**: 240 seconds (accounts for long document analysis)

### 3. Robust JSON Extraction from AI Responses

AI responses typically arrive as markdown-wrapped JSON that may be truncated:

```
```json
{
    "issues": [...],
    "summary": "..."
}
```                                    <-- May be missing if truncated
```

The `_extract_json()` method handles multiple scenarios:

1. **Complete code blocks**: Extract JSON from ` ```json ... ``` ` blocks
2. **Truncated code blocks**: Detect responses starting with ` ```json ` but missing closing fence
3. **Raw JSON**: Fall back to finding `{"issues"` pattern in plain text
4. **Truncated JSON repair**: Find last complete object in arrays, close remaining brackets

```python
def _repair_truncated_json(self, text: str) -> str:
    # Find last complete object by tracking brace depth
    # Truncate at last valid closing brace
    # Close remaining open brackets/braces
```

### 4. AI Response Storage for Debugging

All AI responses are saved to disk for debugging without re-running API calls:

```
data/ai_responses/
├── document_analysis_claude-sonnet-4-5_20251208_121646.txt
├── document_analysis_claude-sonnet-4-5_20251208_121850.txt
└── ...
```

**File naming**: `{operation}_{model}_{timestamp}.txt`

This enables:
- Post-mortem debugging of parsing failures
- Reprocessing responses after fixing extraction bugs
- Cost savings by avoiding redundant API calls

### 5. Prompt Engineering

Prompts are structured using the template pattern:

```
src/infrastructure/ai/prompts/
├── base.py                    # PromptContext dataclass
├── document_analysis.py       # Analysis prompt template
└── suggestion_generation.py   # Suggestion prompt template
```

Analysis prompts instruct the model to return structured JSON with:
- `issues[]`: Array of identified problems with rule_id, severity, location
- `suggestions[]`: Optional array of improvement suggestions
- `summary`: Overall analysis summary

## Consequences

### Positive

- **Single dependency** for multi-model support (LiteLLM) vs multiple SDKs
- **Resilient parsing** handles real-world AI output variability
- **Debuggable** with stored responses for offline analysis
- **Extensible** - adding new providers requires minimal code changes
- **Cost-efficient** - stored responses prevent redundant API calls during debugging

### Negative

- **LiteLLM dependency** - tied to their release cycle for new model support
- **Storage overhead** - AI responses consume disk space (mitigated by cleanup scripts)
- **Parsing complexity** - robust extraction adds code complexity

### Neutral

- Different models may require prompt adjustments for optimal output
- Token limits vary by model, affecting response truncation frequency

## Alternatives Considered

### Google Agent Development Kit (ADK)

Initially attempted but abandoned due to:
- Pydantic version conflicts with FastAPI
- Additional complexity for orchestration features we don't need
- LiteLLM provides equivalent functionality with simpler integration

### Direct Anthropic SDK

Considered but rejected because:
- Limits future flexibility to add other providers
- LiteLLM wraps the Anthropic SDK with added benefits (retries, unified interface)

### Streaming Responses

Could reduce truncation issues by processing tokens incrementally:
- Rejected for MVP due to added complexity
- May be reconsidered if truncation remains problematic

## References

- [LiteLLM Documentation](https://docs.litellm.ai/)
- [ADR-003: Multi-Model AI Support](003-multi-model-ai-support.md)
- [Anthropic Claude Models](https://docs.anthropic.com/claude/docs/models-overview)
