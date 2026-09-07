from typing import List, Dict, Any

class ReciprocalRankFusion:
    """Reciprocal Rank Fusion (RRF) implementation for merging rank lists."""

    @staticmethod
    def fuse(
        dense_results: List[Dict[str, Any]],
        sparse_results: List[Dict[str, Any]],
        rrf_k: int = 60,
        dense_weight: float = 1.0,
        sparse_weight: float = 1.0
    ) -> List[Dict[str, Any]]:
        """Fuses dense and sparse candidate result sets into a unified ranked list."""
        fused_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict[str, Any]] = {}

        # Process Dense Ranks
        for rank, item in enumerate(dense_results, start=1):
            chunk_id = item["chunk_id"]
            chunk_map[chunk_id] = item
            score = dense_weight * (1.0 / (rrf_k + rank))
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + score
            item["dense_rank"] = rank

        # Process Sparse Ranks
        for rank, item in enumerate(sparse_results, start=1):
            chunk_id = item["chunk_id"]
            if chunk_id not in chunk_map:
                chunk_map[chunk_id] = item
            else:
                chunk_map[chunk_id]["sparse_score"] = item.get("sparse_score")
            score = sparse_weight * (1.0 / (rrf_k + rank))
            fused_scores[chunk_id] = fused_scores.get(chunk_id, 0.0) + score
            chunk_map[chunk_id]["sparse_rank"] = rank

        # Sort merged chunks by fused RRF score descending
        sorted_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)

        fused_results = []
        for cid in sorted_ids:
            chunk = chunk_map[cid].copy()
            chunk["score"] = fused_scores[cid]
            chunk["rrf_score"] = fused_scores[cid]
            fused_results.append(chunk)

        return fused_results
