from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag.pipeline import answer_query

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Submit a legal-research query and return answer text with citations."""
    return answer_query(request.message, request.language)
