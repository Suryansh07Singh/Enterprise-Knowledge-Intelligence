import re
from typing import List, Dict, Any, Optional
from app.generation.llm_factory import llm_factory
from app.core.logging import logger

class QueryIntelligence:
    """Query transformation module handling conversational rewriting, decomposition, and multi-query expansion."""

    @staticmethod
    async def rewrite_query(current_query: str, history: List[Dict[str, str]]) -> str:
        """Rewrites conversational follow-up questions into self-contained search queries."""
        if not history:
            return current_query.strip()

        # Heuristic fast check for obvious follow-ups ("What about international?", "What is its limit?")
        is_follow_up = any(w in current_query.lower() for w in ["what about", "how about", "its", "it", "they", "that", "this", "also", "and"])
        if not is_follow_up and len(current_query.split()) > 5:
            return current_query.strip()

        history_summary = "\n".join([f"{m['sender'].upper()}: {m['content']}" for m in history[-4:]])
        prompt = (
            f"Given the following conversation history and follow-up question, rewrite the follow-up question "
            f"into a single standalone search query that preserves all relevant context.\n\n"
            f"CONVERSATION HISTORY:\n{history_summary}\n\n"
            f"FOLLOW-UP QUESTION: {current_query}\n\n"
            f"STANDALONE SEARCH QUERY:"
        )

        try:
            provider = llm_factory.get_provider()
            rewritten = await provider.generate(prompt, system_instruction="You are a query rewriting assistant. Output ONLY the rewritten standalone query.")
            clean_q = rewritten.strip().strip('"').strip("'")
            logger.info(f"Rewrote query '{current_query}' -> '{clean_q}'")
            return clean_q if len(clean_q) > 3 else current_query
        except Exception as e:
            logger.error(f"Query rewrite failed: {e}")
            return current_query

    @staticmethod
    def generate_multi_queries(query: str) -> List[str]:
        """Generates variations of a query for multi-query retrieval expansion."""
        queries = [query]
        # Clean query variations
        if "?" in query:
            queries.append(query.replace("?", ""))
        return list(set(queries))
