from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag.pipeline import answer_query
from app.services.session_store import add_message, list_sessions

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Submit a legal-research query and return answer text with citations."""
    session_id = request.session_id or uuid.uuid4().hex[:12]

    # Record the user message
    add_message(session_id, "user", request.message)

    result = answer_query(request.message, request.language)

    # Record the assistant response
    add_message(session_id, "assistant", result.answer, {"citations_count": len(result.citations)})

    # Attach session_id so the frontend can keep appending
    result.session_id = session_id
    return result


@router.get("/history")
def chat_history() -> list[dict]:
    """Return all chat sessions for the sidebar."""
    return list_sessions()
