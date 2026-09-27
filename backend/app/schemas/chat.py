from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    file_number: str
    title: str
    volume: str
    page: str
    bench: str
    binding_status: str = "Illustrative record"


class ChatRequest(BaseModel):
    message: str = Field(min_length=3, max_length=4000)
    language: str = Field(default="auto", pattern="^(auto|en|am)$")

    @field_validator("message")
    @classmethod
    def message_must_contain_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must contain text")
        return value


class ChatResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation]
    disclaimer: str
