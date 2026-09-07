import time
from typing import List, Dict, Any, AsyncGenerator, Tuple
from app.generation.llm_factory import llm_factory
from app.generation.context_builder import context_builder
from app.generation.guardrails import guardrails
from app.core.logging import logger

class GroundedGenerator:
    """Grounded answer generator enforcing evidence verification and citation formatting."""

    async def generate_response(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]],
        rewritten_query: str = None
    ) -> Dict[str, Any]:
        """Generates grounded answer and citation metadata."""
        t0 = time.perf_counter()

        # 1. Abstention check
        should_abstain, confidence = guardrails.check_abstention(retrieved_chunks)
        if should_abstain:
            return {
                "answer": guardrails.ABSTENTION_MESSAGE,
                "citations": [],
                "confidence": confidence,
                "grounded": False,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2)
            }

        # 2. Build Context
        ctx = context_builder.build_context(retrieved_chunks)
        formatted_context = ctx["formatted_context"]
        citations = ctx["citations_metadata"]

        # 3. Formulate Prompt
        search_query = rewritten_query or query
        prompt = (
            f"USER QUERY: {search_query}\n\n"
            f"CONTEXT EVIDENCE:\n{formatted_context}\n\n"
            f"Provide a clear, grounded answer using ONLY the context evidence above. "
            f"Include exact citations matching document names and sections."
        )

        # 4. Generate with LLM
        system_instruction = guardrails.get_system_prompt()
        provider = llm_factory.get_provider()

        answer = await provider.generate(prompt, system_instruction=system_instruction)
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        return {
            "answer": answer if answer else guardrails.ABSTENTION_MESSAGE,
            "citations": citations,
            "confidence": confidence,
            "grounded": True if answer else False,
            "latency_ms": latency_ms
        }

    async def generate_stream_response(
        self,
        query: str,
        retrieved_chunks: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """Streams response tokens progressively."""
        should_abstain, confidence = guardrails.check_abstention(retrieved_chunks)
        if should_abstain:
            yield guardrails.ABSTENTION_MESSAGE
            return

        ctx = context_builder.build_context(retrieved_chunks)
        prompt = (
            f"USER QUERY: {query}\n\n"
            f"CONTEXT EVIDENCE:\n{ctx['formatted_context']}\n\n"
            f"Answer the query using ONLY the context evidence."
        )

        provider = llm_factory.get_provider()
        async for token in provider.generate_stream(prompt, system_instruction=guardrails.get_system_prompt()):
            yield token

grounded_generator = GroundedGenerator()
