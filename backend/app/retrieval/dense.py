import numpy as np
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from app.core.config import settings
from app.core.logging import logger

class Embedder:
    """Configurable embedding model wrapper using sentence-transformers with fallback."""
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
                cls._model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            except Exception as e:
                logger.warning(f"Could not load SentenceTransformer ({e}). Using fallback pseudo-embedder.")
                cls._model = "fallback"
        return cls._model

    @classmethod
    def embed_texts(cls, texts: List[str]) -> List[List[float]]:
        model = cls.get_model()
        if model == "fallback":
            return [cls._fallback_embed(t) for t in texts]
        embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        return embeddings.tolist()

    @classmethod
    def embed_query(cls, query: str) -> List[float]:
        return cls.embed_texts([query])[0]

    @staticmethod
    def _fallback_embed(text: str) -> List[float]:
        """Deterministic fallback vector generator for testing/offline mode."""
        rng = np.random.RandomState(abs(hash(text)) % (2**31))
        vec = rng.randn(settings.EMBEDDING_DIMENSION)
        norm = np.linalg.norm(vec)
        return (vec / norm).tolist() if norm > 0 else vec.tolist()

class QdrantDenseStore:
    """Qdrant vector store supporting dense retrieval and payload filtering."""
    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            # Try connecting to local Qdrant container or host
            self.client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=2.0)
            self.client.get_collections()
            logger.info("Connected to Qdrant vector database.")
        except Exception as e:
            logger.warning(f"Qdrant server not reachable at {settings.QDRANT_HOST}:{settings.QDRANT_PORT} ({e}). Using in-memory Qdrant client.")
            self.client = QdrantClient(":memory:")

        self.ensure_collection()

    def ensure_collection(self):
        try:
            collections = [c.name for c in self.client.get_collections().collections]
            if settings.QDRANT_COLLECTION_NAME not in collections:
                self.client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(size=settings.EMBEDDING_DIMENSION, distance=Distance.COSINE)
                )
                logger.info(f"Created Qdrant collection: {settings.QDRANT_COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"Error ensuring Qdrant collection: {e}")

    def insert_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        if not chunks:
            return True
            
        texts = [c["text"] for c in chunks]
        embeddings = Embedder.embed_texts(texts)

        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, embeddings)):
            points.append(PointStruct(
                id=chunk.get("id", str(hash(f"{chunk['document_id']}_{chunk['chunk_index']}"))),
                vector=vector,
                payload=chunk
            ))

        try:
            self.client.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=points
            )
            return True
        except Exception as e:
            logger.error(f"Failed to upsert chunks to Qdrant: {e}")
            return False

    def search(
        self,
        query: str,
        user_roles: List[str],
        department: str,
        top_k: int = 25
    ) -> List[Dict[str, Any]]:
        query_vector = Embedder.embed_query(query)

        # Security & RBAC payload filtering
        allowed_access_levels = ["public", "employee"]
        roles_lower = [r.lower() for r in user_roles]

        if "admin" in roles_lower:
            allowed_access_levels.extend(
                ["hr", "finance", "engineering", "admin", "confidential"]
            )

        if "hr" in roles_lower:
            allowed_access_levels.append("hr")

        if "finance" in roles_lower:
            allowed_access_levels.append("finance")

        if "engineering" in roles_lower:
            allowed_access_levels.append("engineering")

        # Qdrant search
        try:
            if hasattr(self.client, "query_points"):
                res_obj = self.client.query_points(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    query=query_vector,
                    limit=top_k
                )
                results = res_obj.points

            elif hasattr(self.client, "search"):
                results = self.client.search(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    query_vector=query_vector,
                    limit=top_k
                )

            else:
                logger.error("Qdrant client has no supported search method.")
                return []

        except Exception as e:
            logger.error(f"Dense vector search failed: {e}")
            return []

        # Convert Qdrant results into application format
        hits = []

        for res in results:
            payload = res.payload or {}

            acc = payload.get("access_level", "employee").lower()
            doc_dept = payload.get("department", "General")

            # RBAC Verification
            if (
                acc not in allowed_access_levels
                and doc_dept != department
                and "admin" not in roles_lower
            ):
                continue

            hits.append({
                "chunk_id": str(res.id),
                "document_id": payload.get("document_id"),
                "document_name": payload.get("document_name"),
                "text": payload.get("text"),
                "page_number": payload.get("page_number", 1),
                "section_title": payload.get("section_title", "General"),
                "department": payload.get("department", "General"),
                "access_level": payload.get("access_level", "employee"),
                "score": float(res.score),
                "dense_score": float(res.score)
            })

        return hits

    def delete_document_chunks(self, document_id: str):
        try:
            self.client.delete(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points_selector=Filter(
                    must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]
                )
            )
        except Exception as e:
            logger.error(f"Error deleting Qdrant chunks for document {document_id}: {e}")

qdrant_store = QdrantDenseStore()
