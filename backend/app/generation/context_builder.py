import hashlib
from typing import List, Dict, Any

class ContextBuilder:
    """Constructs structured evidence context for LLM generation while enforcing token budget & XML isolation."""

    def __init__(self, max_word_budget: int = 2500):
        self.max_word_budget = max_word_budget

    def build_context(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Deduplicates, orders, and builds structured evidence context from retrieved chunks."""
        seen_hashes = set()
        deduped_chunks = []
        total_words = 0

        for chunk in chunks:
            text = chunk.get("text", "").strip()
            if not text:
                continue

            # SHA256 deduplication
            t_hash = hashlib.sha256(text.lower().encode("utf-8")).hexdigest()
            if t_hash in seen_hashes:
                continue
            seen_hashes.add(t_hash)

            words = len(text.split())
            if total_words + words > self.max_word_budget:
                break

            deduped_chunks.append(chunk)
            total_words += words

        # Format XML evidence blocks
        evidence_blocks = []
        citations_metadata = []

        for idx, chunk in enumerate(deduped_chunks, start=1):
            doc_name = chunk.get("document_name", "Unknown")
            page_num = chunk.get("page_number", 1)
            section = chunk.get("section_title", "General")
            text = chunk.get("text", "")

            block = (
                f'<evidence id="{idx}" document="{doc_name}" page="{page_num}" section="{section}">\n'
                f'{text}\n'
                f'</evidence>'
            )
            evidence_blocks.append(block)

            citations_metadata.append({
                "document_id": chunk.get("document_id", ""),
                "document_name": doc_name,
                "page": page_num,
                "section": section,
                "excerpt": text[:150] + "..." if len(text) > 150 else text,
                "score": chunk.get("score")
            })

        formatted_context = "\n\n".join(evidence_blocks)

        return {
            "formatted_context": formatted_context,
            "chunks": deduped_chunks,
            "citations_metadata": citations_metadata,
            "total_words": total_words,
            "chunk_count": len(deduped_chunks)
        }

context_builder = ContextBuilder()
