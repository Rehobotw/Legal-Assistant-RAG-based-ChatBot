from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag.pipeline import answer_query
from app.services.session_store import add_message, delete_session, get_session, list_sessions

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Submit a legal-research query and return answer text with citations."""
    session_id = request.session_id or uuid.uuid4().hex[:12]

    # Record the user message
    add_message(session_id, "user", request.message)

    result = answer_query(request.message, request.language)

    # Record the assistant response with citations
    citations_data = [c.model_dump() for c in result.citations] if result.citations else []
    add_message(session_id, "assistant", result.answer, {"citations": citations_data})

    # Attach session_id so the frontend can keep appending
    result.session_id = session_id
    return result


@router.get("/history")
def chat_history() -> list[dict]:
    """Return all chat sessions for the sidebar."""
    return list_sessions()


@router.get("/history/{session_id}")
def chat_session_detail(session_id: str) -> dict:
    """Return full message history for a specific chat session."""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.delete("/history/{session_id}")
def delete_chat_session(session_id: str) -> dict:
    """Delete a chat session from history."""
    success = delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "deleted", "session_id": session_id}

