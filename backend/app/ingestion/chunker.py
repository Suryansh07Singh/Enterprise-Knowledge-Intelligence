import re
from typing import List, Dict, Any

class IntelligentChunker:
    """Section and paragraph aware text chunker with lineage tracking.
    Maintains semantic boundaries while respecting token/character limits.
    """
    
    def __init__(self, chunk_size: int = 500, overlap: int = 50, min_chunk_size: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size

    def chunk_document(
        self,
        parsed_pages: List[Dict[str, Any]],
        doc_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Chunks parsed document pages while preserving page, section lineage and metadata."""
        chunks = []
        chunk_index = 0

        for page in parsed_pages:
            page_num = page.get("page_number", 1)
            section = page.get("section_title", "General")
            text = page.get("text", "")
            
            if not text:
                continue

            # Split section into paragraphs
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            
            current_chunk_words = []
            current_word_count = 0
            
            for para in paragraphs:
                words = para.split()
                if not words:
                    continue

                if current_word_count + len(words) <= self.chunk_size:
                    current_chunk_words.extend(words)
                    current_word_count += len(words)
                else:
                    # If adding paragraph exceeds chunk_size, finalize current chunk if above min size
                    if current_word_count >= self.min_chunk_size:
                        chunk_text = " ".join(current_chunk_words)
                        chunks.append(self._build_chunk_dict(chunk_text, chunk_index, page_num, section, doc_metadata))
                        chunk_index += 1
                        
                        # Overlap: keep last `overlap` words
                        overlap_words = current_chunk_words[-self.overlap:] if self.overlap < len(current_chunk_words) else []
                        current_chunk_words = overlap_words + words
                        current_word_count = len(current_chunk_words)
                    else:
                        current_chunk_words.extend(words)
                        current_word_count += len(words)

            if current_chunk_words and current_word_count >= self.min_chunk_size:
                chunk_text = " ".join(current_chunk_words)
                chunks.append(self._build_chunk_dict(chunk_text, chunk_index, page_num, section, doc_metadata))
                chunk_index += 1

        return chunks

    def _build_chunk_dict(
        self,
        text: str,
        chunk_index: int,
        page_number: int,
        section_title: str,
        doc_meta: Dict[str, Any]
    ) -> Dict[str, Any]:
        word_count = len(text.split())
        return {
            "chunk_index": chunk_index,
            "text": text,
            "token_count": int(word_count * 1.3),  # Approximate token ratio
            "page_number": page_number,
            "section_title": section_title,
            "document_id": doc_meta.get("id"),
            "document_name": doc_meta.get("name"),
            "department": doc_meta.get("department", "General"),
            "access_level": doc_meta.get("access_level", "employee"),
            "version": doc_meta.get("version", "1.0")
        }
