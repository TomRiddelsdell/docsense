import asyncio
import json
import os
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from google import genai
from google.genai import types

from src.api.schemas.parameters import Parameter, ParametersResponse
from src.api.dependencies import get_document_by_id_handler
from src.application.queries.document_queries import GetDocumentById

router = APIRouter()


PARAMETER_EXTRACTION_PROMPT = """Analyze the following trading algorithm documentation and extract all trading parameters.

For each parameter found, identify:
1. A unique identifier (lowercase, underscores, e.g., "max_position_size")
2. The parameter name as written in the document
3. A brief description of what the parameter controls
4. The type (one of: numeric, percentage, duration, boolean, text, ratio)
5. The value if specified in the document
6. Dependencies - other parameters this one depends on (by their ids)
7. The section of the document where it was found

Return a JSON object with this structure:
{
  "parameters": [
    {
      "id": "parameter_id",
      "name": "Parameter Name",
      "description": "What this parameter does",
      "type": "numeric",
      "value": "100",
      "dependencies": ["other_param_id"],
      "section": "Risk Management"
    }
  ]
}

Look for:
- Position sizes, limits, thresholds
- Risk parameters (stop loss, take profit, max drawdown)
- Time-based parameters (holding periods, rebalance frequency)
- Technical indicators and their settings
- Entry/exit conditions with numeric thresholds
- Portfolio allocation percentages
- Leverage ratios

Document to analyze:
"""


def get_gemini_client():
    api_key = os.environ.get("AI_INTEGRATIONS_GEMINI_API_KEY")
    base_url = os.environ.get("AI_INTEGRATIONS_GEMINI_BASE_URL")
    
    if not api_key or not base_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is not configured"
        )
    
    return genai.Client(
        api_key=api_key,
        http_options={
            'api_version': '',
            'base_url': base_url
        }
    )


@router.get("/documents/{document_id}/parameters", response_model=ParametersResponse)
async def get_document_parameters(
    document_id: UUID,
    handler=Depends(get_document_by_id_handler),
):
    query = GetDocumentById(document_id=document_id)
    document = await handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    if not document.markdown_content:
        return ParametersResponse(
            document_id=document_id,
            parameters=[],
            total=0,
        )

    prompt = PARAMETER_EXTRACTION_PROMPT + document.markdown_content

    try:
        client = get_gemini_client()
        
        response = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Content(
                            role="user",
                            parts=[types.Part(text=prompt)]
                        )
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3,
                    )
                )
            ),
            timeout=60,
        )
        
        result_data = json.loads(response.text or "{}")
        raw_params = result_data.get("parameters", [])
        
        parameters = []
        for p in raw_params:
            try:
                param = Parameter(
                    id=p.get("id", str(uuid4())[:8]),
                    name=p.get("name", "Unknown"),
                    description=p.get("description"),
                    type=p.get("type", "text"),
                    value=p.get("value"),
                    dependencies=p.get("dependencies", []),
                    section=p.get("section"),
                )
                parameters.append(param)
            except Exception:
                continue
        
        return ParametersResponse(
            document_id=document_id,
            parameters=parameters,
            total=len(parameters),
        )
        
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI service request timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract parameters: {str(e)}"
        )
