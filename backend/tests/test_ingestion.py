import pytest
from app.ingestion.chunker import IntelligentChunker
from app.ingestion.parser import DocumentParser

def test_intelligent_chunker():
    chunker = IntelligentChunker(chunk_size=20, overlap=5, min_chunk_size=5)
    parsed_pages = [
        {
            "page_number": 1,
            "section_title": "International Travel Policy",
            "text": "The maximum reimbursement allowed for international business travel is capped at 250 dollars per day for meals and incidental expenses."
        }
    ]
    meta = {"id": "doc-123", "name": "Policy.pdf", "department": "Finance", "access_level": "employee"}
    chunks = chunker.chunk_document(parsed_pages, meta)

    assert len(chunks) >= 1
    assert chunks[0]["page_number"] == 1
    assert chunks[0]["section_title"] == "International Travel Policy"
    assert chunks[0]["department"] == "Finance"
    assert "reimbursement" in chunks[0]["text"]
