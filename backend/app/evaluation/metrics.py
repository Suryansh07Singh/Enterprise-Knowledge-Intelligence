import math
from typing import List, Dict, Any, Set

class EvaluationMetrics:
    """Calculates Information Retrieval (IR) and RAG generation quality metrics."""

    @staticmethod
    def recall_at_k(retrieved_docs: List[str], ground_truth_docs: List[str], k: int) -> float:
        """Recall@K = |Retrieved@K ∩ Relevant| / |Relevant|"""
        if not ground_truth_docs:
            return 1.0  # If no relevant docs expected (e.g. abstention test), 1.0 if none retrieved or irrelevant
        top_k = retrieved_docs[:k]
        hits = set(top_k).intersection(set(ground_truth_docs))
        return len(hits) / float(len(ground_truth_docs))

    @staticmethod
    def precision_at_k(retrieved_docs: List[str], ground_truth_docs: List[str], k: int) -> float:
        """Precision@K = |Retrieved@K ∩ Relevant| / K"""
        if k == 0:
            return 0.0
        top_k = retrieved_docs[:k]
        hits = set(top_k).intersection(set(ground_truth_docs))
        return len(hits) / float(k)

    @staticmethod
    def mrr(retrieved_docs: List[str], ground_truth_docs: List[str]) -> float:
        """Mean Reciprocal Rank (MRR) = 1 / rank of first relevant doc."""
        if not ground_truth_docs:
            return 1.0
        gt_set = set(ground_truth_docs)
        for rank, doc in enumerate(retrieved_docs, start=1):
            if doc in gt_set:
                return 1.0 / float(rank)
        return 0.0

    @staticmethod
    def ndcg_at_k(retrieved_docs: List[str], ground_truth_docs: List[str], k: int) -> float:
        """Normalized Discounted Cumulative Gain at K (nDCG@K)."""
        if not ground_truth_docs:
            return 1.0
        gt_set = set(ground_truth_docs)

        # DCG calculation
        dcg = 0.0
        for i, doc in enumerate(retrieved_docs[:k]):
            rel = 1.0 if doc in gt_set else 0.0
            dcg += rel / math.log2(i + 2)

        # Ideal DCG calculation
        idcg = 0.0
        for i in range(min(len(ground_truth_docs), k)):
            idcg += 1.0 / math.log2(i + 2)

        return (dcg / idcg) if idcg > 0 else 0.0

    @staticmethod
    def faithfulness_score(generated_answer: str, context_text: str) -> float:
        """Evaluates whether claims in generated answer are present in context."""
        if not generated_answer:
            return 0.0
        if "couldn't find sufficient evidence" in generated_answer.lower():
            return 1.0
        
        words = [w.lower() for w in generated_answer.split() if len(w) > 4]
        if not words:
            return 1.0
        ctx_lower = context_text.lower()
        matches = sum(1 for w in words if w in ctx_lower)
        return float(matches) / float(len(words))
