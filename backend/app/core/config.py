import os
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Enterprise Knowledge Intelligence Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENV: str = os.getenv("ENV", "development")
    DEBUG: bool = True
    
    # Security / Auth
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-enterprise-rag-key-change-in-production-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./enterprise_rag.db"
    )
    
    # Redis Cache & Task Queue
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Qdrant Vector DB
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_API_KEY: Optional[str] = os.getenv("QDRANT_API_KEY", None)
    QDRANT_COLLECTION_NAME: str = "enterprise_knowledge_chunks"
    
    # LLM Providers & Models

    PRIMARY_LLM_PROVIDER: str = os.getenv("PRIMARY_LLM_PROVIDER", "openrouter")
    FALLBACK_LLM_PROVIDER: str = os.getenv("FALLBACK_LLM_PROVIDER", "mock")

    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY", None)
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL","https://openrouter.ai/api/v1")

    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)

    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    
    # Embeddings & Reranking
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = 384
    RERANKER_MODEL_NAME: str = os.getenv("RERANKER_MODEL_NAME", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    # Retrieval Hyperparameters
    DENSE_TOP_K: int = 25
    SPARSE_TOP_K: int = 25
    RRF_K: int = 60
    RERANK_TOP_K: int = 5
    ABSTENTION_THRESHOLD: float = 0.25
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        case_sensitive = True

settings = Settings()
