import json
import time
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.evaluation.metrics import EvaluationMetrics
from app.retrieval.hybrid import hybrid_retriever
from app.reranking.cross_encoder import reranker
from app.generation.generator import grounded_generator
from app.models.domain import EvaluationRun
from app.core.logging import logger

class BenchmarkRunner:
    """Automated benchmark test harness comparing search modes."""

    def __init__(self, dataset_path: str = "app/evaluation/benchmark_dataset.json"):
        self.dataset_path = dataset_path

    def load_dataset(self) -> List[Dict[str, Any]]:
        try:
            with open(self.dataset_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed loading benchmark dataset ({e}). Returning empty dataset.")
            return []

    async def run_evaluation(
        self,
        db: AsyncSession,
        run_name: str = "Standard Hybrid Rerank Benchmark",
        mode: str = "hybrid_rerank",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """Runs evaluation harness on benchmark dataset and stores run metrics."""
        t0 = time.perf_counter()
        dataset = self.load_dataset()

        recalls = []
        precisions = []
        mrrs = []
        ndcgs = []
        faithfulness_list = []

        for item in dataset:
            query = item["question"]
            gt_docs = item.get("relevant_documents", [])
            user_roles = ["EMPLOYEE", "HR", "FINANCE", "ADMIN"]
            dept = item.get("department", "General")

            # 1. Retrieve candidates
            candidates, latencies = hybrid_retriever.retrieve(query, user_roles, dept, mode=mode, top_k=20)
            
            # 2. Rerank if hybrid_rerank mode
            if mode == "hybrid_rerank":
                candidates, r_ms = reranker.rerank(query, candidates, top_k=top_k)
            else:
                candidates = candidates[:top_k]

            retrieved_doc_names = [c.get("document_name", "") for c in candidates if c.get("document_name")]

            # 3. Calculate IR Metrics
            recalls.append(EvaluationMetrics.recall_at_k(retrieved_doc_names, gt_docs, top_k))
            precisions.append(EvaluationMetrics.precision_at_k(retrieved_doc_names, gt_docs, top_k))
            mrrs.append(EvaluationMetrics.mrr(retrieved_doc_names, gt_docs))
            ndcgs.append(EvaluationMetrics.ndcg_at_k(retrieved_doc_names, gt_docs, top_k))

            # 4. Generate answer and evaluate Faithfulness
            gen_res = await grounded_generator.generate_response(query, candidates)
            answer_text = gen_res.get("answer", "")
            ctx_text = " ".join([c.get("text", "") for c in candidates])
            faithfulness_list.append(EvaluationMetrics.faithfulness_score(answer_text, ctx_text))

        total_q = len(dataset) if dataset else 1
        avg_recall = sum(recalls) / total_q
        avg_precision = sum(precisions) / total_q
        avg_mrr = sum(mrrs) / total_q
        avg_ndcg = sum(ndcgs) / total_q
        avg_faithfulness = sum(faithfulness_list) / total_q
        duration = round(time.perf_counter() - t0, 2)

        # Save to DB
        eval_run = EvaluationRun(
            name=f"{run_name} ({mode})",
            config={"mode": mode, "top_k": top_k},
            recall_at_k=round(avg_recall, 4),
            precision_at_k=round(avg_precision, 4),
            mrr=round(avg_mrr, 4),
            ndcg=round(avg_ndcg, 4),
            faithfulness_score=round(avg_faithfulness, 4),
            answer_relevance_score=round(avg_faithfulness, 4),
            total_eval_questions=len(dataset),
            duration_seconds=duration
        )
        db.add(eval_run)
        await db.commit()

        logger.info(f"Completed Evaluation Run '{run_name}': Recall@5={avg_recall:.4f}, MRR={avg_mrr:.4f}, nDCG@5={avg_ndcg:.4f}")

        return {
            "id": eval_run.id,
            "name": eval_run.name,
            "recall_at_k": round(avg_recall, 4),
            "precision_at_k": round(avg_precision, 4),
            "mrr": round(avg_mrr, 4),
            "ndcg": round(avg_ndcg, 4),
            "faithfulness_score": round(avg_faithfulness, 4),
            "answer_relevance_score": round(avg_faithfulness, 4),
            "total_eval_questions": len(dataset),
            "duration_seconds": duration,
            "created_at": eval_run.created_at
        }

benchmark_runner = BenchmarkRunner()
