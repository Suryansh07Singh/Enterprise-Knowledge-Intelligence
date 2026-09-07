import time
from typing import List, Dict, Any, Tuple
from app.retrieval.dense import qdrant_store
from app.retrieval.sparse import bm25_store
from app.retrieval.fusion import ReciprocalRankFusion
from app.core.config import settings
from app.core.logging import logger

class HybridRetriever:
    """Enterprise Hybrid Retrieval facade with benchmarking timing per stage."""

    def __init__(self):
        self.dense_store = qdrant_store
        self.sparse_store = bm25_store

    def retrieve(
        self,
        query: str,
        user_roles: List[str],
        department: str,
        mode: str = "hybrid",
        top_k: int = 25
    ) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        """Retrieves chunks based on the requested mode (dense, sparse, hybrid).
        Returns (candidate_chunks, stage_latencies_ms).
        """
        latencies = {
            "embedding_ms": 0.0,
            "vector_ms": 0.0,
            "sparse_ms": 0.0,
            "fusion_ms": 0.0
        }

        if mode == "dense":
            t0 = time.perf_counter()
            results = self.dense_store.search(query, user_roles, department, top_k=top_k)
            latencies["vector_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            return results, latencies

        elif mode == "sparse":
            t0 = time.perf_counter()
            results = self.sparse_store.search(query, user_roles, department, top_k=top_k)
            latencies["sparse_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            return results, latencies

        else:  # hybrid or hybrid_rerank
            t0 = time.perf_counter()
            dense_results = self.dense_store.search(query, user_roles, department, top_k=settings.DENSE_TOP_K)
            latencies["vector_ms"] = round((time.perf_counter() - t0) * 1000, 2)

            t1 = time.perf_counter()
            sparse_results = self.sparse_store.search(query, user_roles, department, top_k=settings.SPARSE_TOP_K)
            latencies["sparse_ms"] = round((time.perf_counter() - t1) * 1000, 2)

            t2 = time.perf_counter()
            fused = ReciprocalRankFusion.fuse(
                dense_results=dense_results,
                sparse_results=sparse_results,
                rrf_k=settings.RRF_K
            )
            latencies["fusion_ms"] = round((time.perf_counter() - t2) * 1000, 2)

            return fused[:top_k], latencies

hybrid_retriever = HybridRetriever()
