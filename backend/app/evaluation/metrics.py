import math
from typing import List


class EvaluationMetrics:
    """Calculates Information Retrieval (IR) and RAG generation quality metrics."""

    @staticmethod
    def recall_at_k(
        retrieved_docs: List[str],
        ground_truth_docs: List[str],
        k: int
    ) -> float:
        """
        Recall@K = relevant documents retrieved in top-K / total relevant documents.

        Returns 0.0 for unanswerable questions because retrieval recall
        is not applicable when no relevant document is expected.
        """
        if not ground_truth_docs:
            return 0.0

        top_k = retrieved_docs[:k]
        hits = set(top_k).intersection(set(ground_truth_docs))

        return len(hits) / float(len(set(ground_truth_docs)))

    @staticmethod
    def precision_at_k(
        retrieved_docs: List[str],
        ground_truth_docs: List[str],
        k: int
    ) -> float:
        """
        Precision@K = relevant retrieved documents / K.

        For unanswerable questions, retrieval precision is not included
        in the aggregate benchmark.
        """
        if not ground_truth_docs or k <= 0:
            return 0.0

        top_k = retrieved_docs[:k]
        hits = set(top_k).intersection(set(ground_truth_docs))

        return len(hits) / float(k)

    @staticmethod
    def mrr(
        retrieved_docs: List[str],
        ground_truth_docs: List[str]
    ) -> float:
        """Mean Reciprocal Rank of the first relevant document."""

        if not ground_truth_docs:
            return 0.0

        gt_set = set(ground_truth_docs)

        for rank, doc in enumerate(retrieved_docs, start=1):
            if doc in gt_set:
                return 1.0 / float(rank)

        return 0.0

    @staticmethod
    def ndcg_at_k(
        retrieved_docs: List[str],
        ground_truth_docs: List[str],
        k: int
    ) -> float:
        """Normalized Discounted Cumulative Gain at K."""

        if not ground_truth_docs:
            return 0.0

        gt_set = set(ground_truth_docs)

        dcg = 0.0

        for i, doc in enumerate(retrieved_docs[:k]):
            relevance = 1.0 if doc in gt_set else 0.0
            dcg += relevance / math.log2(i + 2)

        ideal_relevant = min(len(set(ground_truth_docs)), k)

        idcg = sum(
            1.0 / math.log2(i + 2)
            for i in range(ideal_relevant)
        )

        return (dcg / idcg) if idcg > 0 else 0.0

    @staticmethod
    def faithfulness_score(
        generated_answer: str,
        context_text: str
    ) -> float:
        """
        Lightweight lexical faithfulness indicator.

        Measures how much of the generated answer's meaningful vocabulary
        appears in the retrieved context. This is an indicator, not an
        LLM-judge probability.
        """

        if not generated_answer:
            return 0.0

        answer_lower = generated_answer.lower()

        if (
            "couldn't find sufficient evidence" in answer_lower
            or "insufficient evidence" in answer_lower
        ):
            return 1.0

        words = [
            word.strip(".,!?;:\"'()[]{}")
            for word in generated_answer.split()
            if len(word.strip(".,!?;:\"'()[]{}")) > 4
        ]

        if not words:
            return 1.0

        ctx_lower = context_text.lower()

        matches = sum(
            1 for word in words
            if word in ctx_lower
        )

        return matches / float(len(words))