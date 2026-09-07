import time
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.domain import User
from app.schemas.pydantic_models import SearchRequest, SearchResponse, SearchResultChunk
from app.retrieval.hybrid import hybrid_retriever
from app.reranking.cross_encoder import reranker
from app.generation.guardrails import guardrails

router = APIRouter(prefix="/search", tags=["Search"])

@router.post("", response_model=SearchResponse)
async def search_knowledge_base(
    req: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    t0 = time.perf_counter()
    clean_query = guardrails.sanitize_user_query(req.query)

    # Execute RBAC-enforced retrieval
    candidates, latencies = hybrid_retriever.retrieve(
        query=clean_query,
        user_roles=current_user.roles,
        department=current_user.department,
        mode=req.mode,
        top_k=req.top_k * 2
    )

    if req.mode == "hybrid_rerank" and candidates:
        results, r_ms = reranker.rerank(clean_query, candidates, top_k=req.top_k)
    else:
        results = candidates[:req.top_k]

    formatted_results = []
    for r in results:
        formatted_results.append(SearchResultChunk(
            chunk_id=r.get("chunk_id", ""),
            document_id=r.get("document_id", ""),
            document_name=r.get("document_name", "Unknown"),
            text=r.get("text", ""),
            page_number=r.get("page_number", 1),
            section_title=r.get("section_title", "General"),
            department=r.get("department", "General"),
            access_level=r.get("access_level", "employee"),
            score=r.get("score", 0.0),
            dense_score=r.get("dense_score"),
            sparse_score=r.get("sparse_score"),
            rerank_score=r.get("rerank_score")
        ))

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    return SearchResponse(
        query=req.query,
        mode=req.mode,
        total_results=len(formatted_results),
        results=formatted_results,
        latency_ms=latency_ms
    )
