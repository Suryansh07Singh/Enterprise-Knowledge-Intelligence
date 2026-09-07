import pytest
from app.retrieval.fusion import ReciprocalRankFusion
from app.retrieval.sparse import BM25SparseStore

def test_rrf_fusion():
    dense_results = [
        {"chunk_id": "c1", "score": 0.9, "text": "Chunk 1"},
        {"chunk_id": "c2", "score": 0.8, "text": "Chunk 2"}
    ]
    sparse_results = [
        {"chunk_id": "c2", "score": 12.0, "text": "Chunk 2"},
        {"chunk_id": "c3", "score": 8.0, "text": "Chunk 3"}
    ]

    fused = ReciprocalRankFusion.fuse(dense_results, sparse_results, rrf_k=60)
    assert len(fused) == 3
    # c2 appears in both lists, so its RRF score should be highest!
    assert fused[0]["chunk_id"] == "c2"

def test_bm25_sparse_store():
    store = BM25SparseStore()
    chunks = [
        {
            "id": "c1",
            "document_id": "doc1",
            "document_name": "IT_Policy.pdf",
            "text": "Policy IT-204 requires 16 character password length.",
            "page_number": 1,
            "section_title": "Security",
            "department": "Engineering",
            "access_level": "employee"
        }
    ]
    store.add_chunks(chunks)

    res = store.search("IT-204", user_roles=["EMPLOYEE"], department="Engineering")
    assert len(res) == 1
    assert res[0]["document_name"] == "IT_Policy.pdf"
