from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    file_number: str
    title: str = "Federal Supreme Court Cassation decision"
    date: str = ""
    court: str = "Federal Supreme Court Cassation Division"
    holding: str = ""
    rank: int = 0
    score: float = 0.0
    volume: str = ""
    page: str = ""
    bench: str = ""
    binding_status: str = "Source record — verify in official reporter"


class ChatRequest(BaseModel):
    # A file number or a short Amharic legal term can be a valid lookup.
    message: str = Field(min_length=1, max_length=4000)
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
