from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    thread_id: str = Field(default="default", min_length=1)


class ChatResponse(BaseModel):
    question: str
    answer: str
    need_retrieval: bool = False
    retrieval_query: str = ""
    rewrite_tries: int = 0
    retries: int = 0
    relevant_docs: int = 0
    issup: Optional[str] = None
    isuse: Optional[str] = None
    use_reason: str = ""
    evidence: List[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    filename: str
    chunks_indexed: int
    namespace: str