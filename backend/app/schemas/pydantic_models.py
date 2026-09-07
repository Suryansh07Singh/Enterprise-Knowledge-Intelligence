from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field

# --- Auth Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    roles: List[str]
    department: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    roles: List[str] = Field(default_factory=lambda: ["EMPLOYEE"])
    department: str = "General"

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    roles: List[str]
    department: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- Document & Job Schemas ---
class DocumentResponse(BaseModel):
    id: str
    name: str
    file_type: str
    size_bytes: int
    department: str
    access_level: str
    version: str
    total_pages: int
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class IngestionJobResponse(BaseModel):
    job_id: str
    document_id: str
    status: str
    progress: float
    error_message: Optional[str] = None
    created_at: datetime

# --- Citation & Search Schemas ---
class Citation(BaseModel):
    document_id: str
    document_name: str
    page: int
    section: str
    excerpt: str
    score: Optional[float] = None

class SearchResultChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    text: str
    page_number: int
    section_title: str
    department: str
    access_level: str
    score: float
    dense_score: Optional[float] = None
    sparse_score: Optional[float] = None
    rerank_score: Optional[float] = None

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    mode: str = "hybrid"  # dense, sparse, hybrid, hybrid_rerank

class SearchResponse(BaseModel):
    query: str
    mode: str
    total_results: int
    results: List[SearchResultChunk]
    latency_ms: float

# --- Chat & Conversation Schemas ---
class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    mode: str = "hybrid_rerank"  # dense, sparse, hybrid, hybrid_rerank

class ChatResponse(BaseModel):
    conversation_id: str
    query: str
    rewritten_query: Optional[str] = None
    answer: str
    citations: List[Citation]
    confidence: float
    grounded: bool
    latency_ms: float
    trace_id: str

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender: str
    content: str
    citations: Optional[List[Citation]] = None
    confidence: Optional[float] = None
    grounded: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[MessageResponse]] = None

    class Config:
        from_attributes = True

# --- Metrics & Evaluation Schemas ---
class SystemMetricsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    total_queries: int
    avg_latency_ms: float
    cache_hit_rate: float
    active_users: int

class EvaluationRunRequest(BaseModel):
    name: str = "Standard RAG Benchmark"
    modes: List[str] = Field(default_factory=lambda: ["dense", "sparse", "hybrid", "hybrid_rerank"])

class EvaluationRunResponse(BaseModel):
    id: str
    name: str
    recall_at_k: float
    precision_at_k: float
    mrr: float
    ndcg: float
    faithfulness_score: float
    answer_relevance_score: float
    total_eval_questions: int
    duration_seconds: float
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
