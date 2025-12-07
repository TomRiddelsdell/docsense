import asyncio
import os
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from google import genai
from google.genai import types

from src.api.schemas.chat import ChatRequest, ChatResponse
from src.api.dependencies import get_document_by_id_handler
from src.application.queries.document_queries import GetDocumentById

router = APIRouter()


CHAT_SYSTEM_PROMPT = """You are an expert trading algorithm documentation analyst. You are helping a user understand and improve their trading algorithm documentation.

You have access to the document content and can answer questions about:
- The trading strategy described in the document
- Risk management approaches
- Compliance considerations
- Suggestions for improving the documentation
- Technical implementation details

Be helpful, accurate, and concise in your responses. If you're unsure about something, say so.
Reference specific parts of the document when relevant."""


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


@router.post("/documents/{document_id}/chat", response_model=ChatResponse)
async def chat_with_document(
    document_id: UUID,
    request: ChatRequest,
    handler=Depends(get_document_by_id_handler),
):
    query = GetDocumentById(document_id=document_id)
    document = await handler.handle(query)

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )

    document_context = f"""
Document Title: {document.title or 'Untitled'}
Document Status: {document.status or 'Unknown'}

Document Content:
{document.markdown_content or 'No content available'}
"""

    contents = []
    
    for msg in request.conversation_history:
        role = "user" if msg.role == "user" else "model"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part(text=msg.content)]
            )
        )
    
    user_message = f"""Based on the following document, please answer the user's question.

{document_context}

User Question: {request.message}"""
    
    contents.append(
        types.Content(
            role="user",
            parts=[types.Part(text=user_message)]
        )
    )

    try:
        client = get_gemini_client()
        
        response = await asyncio.wait_for(
            asyncio.to_thread(
                lambda: client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                        system_instruction=CHAT_SYSTEM_PROMPT,
                    )
                )
            ),
            timeout=60,
        )
        
        response_text = response.text or "I couldn't generate a response. Please try again."
        
        return ChatResponse(
            document_id=document_id,
            message=response_text,
            timestamp=datetime.utcnow(),
        )
        
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI service request timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate response: {str(e)}"
        )
