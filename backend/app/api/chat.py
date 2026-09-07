import time
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.domain import User, Conversation, Message, QueryLog
from app.schemas.pydantic_models import ChatRequest, ChatResponse, Citation
from app.generation.query_intelligence import QueryIntelligence
from app.retrieval.hybrid import hybrid_retriever
from app.reranking.cross_encoder import reranker
from app.generation.generator import grounded_generator
from app.generation.guardrails import guardrails
from app.core.redis import redis_client
from app.core.logging import logger, get_trace_id, set_trace_id

router = APIRouter(prefix="/chat", tags=["Chat & RAG Engine"])

@router.post("", response_model=ChatResponse)
async def chat_rag(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    t0 = time.perf_counter()
    trace_id = get_trace_id()
    set_trace_id(trace_id)

    # 1. Conversation Management
    conv = None
    history = []
    if req.conversation_id:
        stmt = select(Conversation).where(Conversation.id == req.conversation_id, Conversation.user_id == current_user.id)
        conv = (await db.execute(stmt)).scalar_one_or_none()

    if not conv:
        conv = Conversation(
            user_id=current_user.id,
            title=req.query[:40] + ("..." if len(req.query) > 40 else "")
        )
        db.add(conv)
        await db.flush()
    else:
        # Load conversation history for query rewriting
        h_stmt = select(Message).where(Message.conversation_id == conv.id).order_by(Message.created_at.asc())
        history_msgs = (await db.execute(h_stmt)).scalars().all()
        history = [{"sender": m.sender, "content": m.content} for m in history_msgs]

    # Save User message
    user_msg = Message(
        conversation_id=conv.id,
        sender="user",
        content=req.query
    )
    db.add(user_msg)
    await db.commit()

    # 2. Redis Caching Check
    cache_key = redis_client.generate_cache_key(
        prefix="rag_query",
        query=req.query,
        user_roles=current_user.roles,
        department=current_user.department
    )
    cached = await redis_client.get_json(cache_key)
    if cached:
        logger.info(f"Cache HIT for query: '{req.query}'")
        # Save assistant message
        asst_msg = Message(
            conversation_id=conv.id,
            sender="assistant",
            content=cached["answer"],
            citations=cached.get("citations", []),
            confidence=cached.get("confidence", 1.0),
            grounded=cached.get("grounded", True)
        )
        db.add(asst_msg)
        await db.commit()

        return ChatResponse(
            conversation_id=conv.id,
            query=req.query,
            rewritten_query=cached.get("rewritten_query"),
            answer=cached["answer"],
            citations=[Citation(**c) for c in cached.get("citations", [])],
            confidence=cached.get("confidence", 1.0),
            grounded=cached.get("grounded", True),
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            trace_id=trace_id
        )

    # 3. Query Sanitization & Rewriting
    clean_query = guardrails.sanitize_user_query(req.query)
    rewritten_q = await QueryIntelligence.rewrite_query(clean_query, history)

    # 4. Retrieval & Reranking
    candidates, latencies = hybrid_retriever.retrieve(
        query=rewritten_q,
        user_roles=current_user.roles,
        department=current_user.department,
        mode=req.mode,
        top_k=20
    )

    t_rerank = time.perf_counter()
    if req.mode == "hybrid_rerank" and candidates:
        top_chunks, rerank_ms = reranker.rerank(rewritten_q, candidates, top_k=5)
    else:
        top_chunks = candidates[:5]
        rerank_ms = 0.0

    # 5. Grounded Response Generation
    gen_result = await grounded_generator.generate_response(clean_query, top_chunks, rewritten_query=rewritten_q)

    # 6. Save Assistant Message & Query Log
    asst_msg = Message(
        conversation_id=conv.id,
        sender="assistant",
        content=gen_result["answer"],
        citations=gen_result.get("citations", []),
        confidence=gen_result.get("confidence", 0.0),
        grounded=gen_result.get("grounded", True)
    )
    db.add(asst_msg)

    total_latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    query_log = QueryLog(
        trace_id=trace_id,
        user_id=current_user.id,
        query=req.query,
        rewritten_query=rewritten_q,
        response=gen_result["answer"],
        total_latency_ms=total_latency_ms,
        vector_latency_ms=latencies.get("vector_ms", 0.0),
        bm25_latency_ms=latencies.get("sparse_ms", 0.0),
        rerank_latency_ms=rerank_ms,
        llm_latency_ms=gen_result.get("latency_ms", 0.0),
        retrieved_chunk_ids=[c.get("chunk_id", "") for c in top_chunks]
    )
    db.add(query_log)
    await db.commit()

    citations_list = [Citation(**c) for c in gen_result.get("citations", [])]

    # Cache successful grounded responses
    if gen_result.get("grounded", True):
        await redis_client.set_json(cache_key, {
            "answer": gen_result["answer"],
            "citations": gen_result.get("citations", []),
            "confidence": gen_result.get("confidence", 1.0),
            "grounded": gen_result.get("grounded", True),
            "rewritten_query": rewritten_q
        }, expire=1800)

    return ChatResponse(
        conversation_id=conv.id,
        query=req.query,
        rewritten_query=rewritten_q,
        answer=gen_result["answer"],
        citations=citations_list,
        confidence=gen_result.get("confidence", 0.0),
        grounded=gen_result.get("grounded", True),
        latency_ms=total_latency_ms,
        trace_id=trace_id
    )

@router.get("/stream")
async def chat_stream(
    query: str = Query(...),
    mode: str = Query("hybrid_rerank"),
    current_user: User = Depends(get_current_user)
):
    """Server-Sent Events (SSE) endpoint for streaming LLM tokens."""
    async def event_generator():
        candidates, _ = hybrid_retriever.retrieve(
            query=query,
            user_roles=current_user.roles,
            department=current_user.department,
            mode=mode,
            top_k=20
        )
        if mode == "hybrid_rerank" and candidates:
            top_chunks, _ = reranker.rerank(query, candidates, top_k=5)
        else:
            top_chunks = candidates[:5]

        async for token in grounded_generator.generate_stream_response(query, top_chunks):
            yield {"event": "token", "data": token}
            
        yield {"event": "end", "data": "[DONE]"}

    return EventSourceResponse(event_generator())
