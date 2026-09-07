import re
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from app.core.logging import logger

class BM25SparseStore:
    """BM25 Sparse Keyword Search Index with metadata and permission filtering."""
    def __init__(self):
        self.chunks: List[Dict[str, Any]] = []
        self.corpus_tokens: List[List[str]] = []
        self.bm25: BM25Okapi = None

    def tokenize(self, text: str) -> List[str]:
        """Alphanumeric tokenizer preserving hyphens, codes, and individual tokens."""
        text_clean = re.sub(r'[^\w\s-]', ' ', text.lower())
        tokens = []
        for word in text_clean.split():
            if len(word) >= 1:
                tokens.append(word)
                if '-' in word:
                    tokens.extend([w for w in word.split('-') if len(w) >= 1])
        return tokens

    def add_chunks(self, chunks: List[Dict[str, Any]]):
        for chunk in chunks:
            self.chunks.append(chunk)
            tokens = self.tokenize(chunk["text"])
            self.corpus_tokens.append(tokens)
        
        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)
            logger.info(f"Re-indexed BM25 sparse index with {len(self.chunks)} total chunks.")

    def search(
        self,
        query: str,
        user_roles: List[str],
        department: str,
        top_k: int = 25
    ) -> List[Dict[str, Any]]:
        if not self.bm25 or not self.chunks:
            return []

        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k * 2]

        allowed_access_levels = ["public", "employee"]
        roles_lower = [r.lower() for r in user_roles]
        if "admin" in roles_lower:
            allowed_access_levels.extend(["hr", "finance", "engineering", "admin", "confidential"])
        if "hr" in roles_lower:
            allowed_access_levels.append("hr")
        if "finance" in roles_lower:
            allowed_access_levels.append("finance")
        if "engineering" in roles_lower:
            allowed_access_levels.append("engineering")

        results = []
        for idx in top_indices:
            score = float(scores[idx])

            chunk = self.chunks[idx]
            acc = chunk.get("access_level", "employee").lower()
            doc_dept = chunk.get("department", "General")

            # RBAC Verification Filter
            if acc not in allowed_access_levels and doc_dept != department and "admin" not in roles_lower:
                continue

            results.append({
                "chunk_id": chunk.get("id", f"{chunk.get('document_id')}_{chunk.get('chunk_index', 0)}"),
                "document_id": chunk.get("document_id"),
                "document_name": chunk.get("document_name"),
                "text": chunk.get("text"),
                "page_number": chunk.get("page_number", 1),
                "section_title": chunk.get("section_title", "General"),
                "department": chunk.get("department", "General"),
                "access_level": chunk.get("access_level", "employee"),
                "score": score,
                "sparse_score": score
            })

            if len(results) >= top_k:
                break

        return results

    def remove_document_chunks(self, document_id: str):
        keep_indices = [i for i, c in enumerate(self.chunks) if c.get("document_id") != document_id]
        self.chunks = [self.chunks[i] for i in keep_indices]
        self.corpus_tokens = [self.corpus_tokens[i] for i in keep_indices]
        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)
        else:
            self.bm25 = None

bm25_store = BM25SparseStore()
