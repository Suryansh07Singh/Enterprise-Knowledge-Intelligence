import time
from typing import List, Dict, Any, Tuple
from app.core.config import settings
from app.core.logging import logger

class CrossEncoderReranker:
    """Cross-Encoder reranker using ms-marco-MiniLM-L-6-v2 with fallback heuristic."""
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading Cross-Encoder model: {settings.RERANKER_MODEL_NAME}")
                cls._model = CrossEncoder(settings.RERANKER_MODEL_NAME)
            except Exception as e:
                logger.warning(f"Could not load CrossEncoder ({e}). Using fallback token overlap reranker.")
                cls._model = "fallback"
        return cls._model

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Reranks top candidate chunks and returns (reranked_chunks, rerank_latency_ms)."""
        if not candidates:
            return [], 0.0

        t0 = time.perf_counter()
        model = self.get_model()

        pairs = [[query, c["text"]] for c in candidates]

        if model == "fallback":
            scores = [self._fallback_score(query, c["text"]) for c in candidates]
        else:
            try:
                scores = model.predict(pairs).tolist()
            except Exception as e:
                logger.error(f"CrossEncoder prediction failed ({e}). Falling back to heuristic reranker.")
                scores = [self._fallback_score(query, c["text"]) for c in candidates]

        # Log observability metadata
        reranked = []
        for idx, (cand, score) in enumerate(zip(candidates, scores)):
            c_copy = cand.copy()
            c_copy["initial_rank"] = idx + 1
            c_copy["initial_score"] = cand.get("score", 0.0)
            c_copy["rerank_score"] = float(score)
            c_copy["score"] = float(score)
            reranked.append(c_copy)

        # Sort descending by cross-encoder rerank score
        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)

        for final_rank, item in enumerate(reranked, start=1):
            item["final_rank"] = final_rank

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        return reranked[:top_k], latency_ms

    @staticmethod
    def _fallback_score(query: str, text: str) -> float:
        """Token overlap heuristic fallback for reranking."""
        q_words = set(query.lower().split())
        t_words = set(text.lower().split())
        if not q_words:
            return 0.0
        overlap = len(q_words.intersection(t_words))
        return float(overlap) / float(len(q_words))

reranker = CrossEncoderReranker()
