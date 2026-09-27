from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, field_validator


class Citation(BaseModel):
    case_number: str = ""
    file_number: str = ""
    title: str = "Federal Supreme Court Cassation decision"
    date: str = ""
    court: str = "Federal Supreme Court Cassation Division"
    holding: str = ""
    rank: int = 0
    score: float = 0.0
    similarity_score: float = 0.0
    match_type: str = "semantic"  # "exact_match" or "semantic"
    volume: str = ""
    page: str = ""
    page_number: str = ""
    source_filename: str = ""
    source_file: str = ""
    bench: str = ""
    binding_status: str = "Source record — verify in official reporter"
    # Additional fields for multi-page case citations
    start_page: str = ""
    end_page: str = ""

    def model_post_init(self, __context: Any) -> None:
        # Sync case_number and file_number
        if not self.file_number and self.case_number:
            self.file_number = self.case_number
        elif not self.case_number and self.file_number:
            self.case_number = self.file_number
        
        # Sync page and page_number
        if not self.page and self.page_number:
            self.page = self.page_number
        elif not self.page_number and self.page:
            self.page_number = self.page
        
        # Sync similarity_score and score
        if self.similarity_score == 0.0 and self.score != 0.0:
            self.similarity_score = self.score
        elif self.score == 0.0 and self.similarity_score != 0.0:
            self.score = self.similarity_score
        
        # Sync source_filename and source_file
        if not self.source_filename and self.source_file:
            self.source_filename = self.source_file
        elif not self.source_file and self.source_filename:
            self.source_file = self.source_filename
        
        # Generate page range display in bench if not already set
        if not self.bench or self.bench == "":
            if self.start_page and self.end_page and self.start_page != self.end_page:
                self.bench = f"Pages {self.start_page}-{self.end_page}"
            elif self.start_page:
                self.bench = f"Page {self.start_page}"
            elif self.page or self.page_number:
                self.bench = f"Page {self.page or self.page_number}"


DocumentCitation = Citation


class ChatRequest(BaseModel):
    # A file number or a short Amharic legal term can be a valid lookup.
    message: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="auto", pattern="^(auto|en|am)$")
    session_id: str | None = None

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
    session_id: str | None = None

