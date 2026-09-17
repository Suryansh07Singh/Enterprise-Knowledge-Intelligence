import gc
import numpy as np
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from app.core.config import settings
from app.core.logging import logger


class Embedder:
    """
    Memory-efficient embedding model wrapper.

    - Loads SentenceTransformer only when required
    - Uses CPU
    - Processes texts in small batches
    - Keeps only one model instance in memory
    """

    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(
                    f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}"
                )

                cls._model = SentenceTransformer(
                    settings.EMBEDDING_MODEL_NAME,
                    device="cpu",
                )

                logger.info("Embedding model loaded successfully.")

            except Exception as e:
                logger.warning(
                    f"Could not load SentenceTransformer ({e}). "
                    "Using fallback pseudo-embedder."
                )
                cls._model = "fallback"

        return cls._model

    @classmethod
    def embed_texts(cls, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings in small batches to reduce RAM usage.
        """

        if not texts:
            return []

        model = cls.get_model()

        # Fallback mode
        if model == "fallback":
            return [cls._fallback_embed(text) for text in texts]

        all_embeddings = []

        # Small batch keeps Render's RAM usage low
        batch_size = 4

        logger.info(
            f"Generating embeddings for {len(texts)} chunks "
            f"using batch size {batch_size}."
        )

        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]

            try:
                batch_embeddings = model.encode(
                    batch,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                )

                all_embeddings.extend(batch_embeddings.tolist())

                # Release temporary batch memory
                del batch_embeddings
                del batch

                gc.collect()

                logger.info(
                    f"Embedded {min(start + batch_size, len(texts))}"
                    f"/{len(texts)} chunks."
                )

            except Exception as e:
                logger.error(
                    f"Embedding batch failed at index {start}: {e}"
                )
                raise

        gc.collect()

        return all_embeddings

    @classmethod
    def embed_query(cls, query: str) -> List[float]:
        return cls.embed_texts([query])[0]

    @staticmethod
    def _fallback_embed(text: str) -> List[float]:
        """
        Deterministic fallback vector generator.
        Used when SentenceTransformer cannot be loaded.
        """

        rng = np.random.RandomState(
            abs(hash(text)) % (2**31)
        )

        vec = rng.randn(settings.EMBEDDING_DIMENSION)

        norm = np.linalg.norm(vec)

        return (
            (vec / norm).tolist()
            if norm > 0
            else vec.tolist()
        )


class QdrantDenseStore:
    """
    Qdrant vector store supporting dense retrieval
    and payload filtering.
    """

    def __init__(self):
        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            self.client = QdrantClient(
                url=f"https://{settings.QDRANT_HOST}",
                api_key=settings.QDRANT_API_KEY,
                timeout=10.0,
            )

            self.client.get_collections()

            logger.info(
                "Connected to Qdrant vector database."
            )

        except Exception as e:
            logger.warning(
                f"Qdrant server not reachable at "
                f"{settings.QDRANT_HOST}:{settings.QDRANT_PORT} "
                f"({e}). Using in-memory Qdrant client."
            )

            self.client = QdrantClient(":memory:")

        self.ensure_collection()

    def ensure_collection(self):
        try:
            collections = [
                c.name
                for c in self.client.get_collections().collections
            ]

            if settings.QDRANT_COLLECTION_NAME not in collections:
                self.client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=settings.EMBEDDING_DIMENSION,
                        distance=Distance.COSINE,
                    ),
                )

                logger.info(
                    f"Created Qdrant collection: "
                    f"{settings.QDRANT_COLLECTION_NAME}"
                )

        except Exception as e:
            logger.error(
                f"Error ensuring Qdrant collection: {e}"
            )

    def insert_chunks(
        self,
        chunks: List[Dict[str, Any]]
    ) -> bool:

        if not chunks:
            return True

        logger.info(
            f"Indexing {len(chunks)} chunks into Qdrant."
        )

        texts = [c["text"] for c in chunks]

        # Memory-efficient embedding generation
        embeddings = Embedder.embed_texts(texts)

        points = []

        for chunk, vector in zip(chunks, embeddings):

            points.append(
                PointStruct(
                    id=chunk.get(
                        "id",
                        str(
                            hash(
                                f"{chunk['document_id']}_"
                                f"{chunk['chunk_index']}"
                            )
                        ),
                    ),
                    vector=vector,
                    payload=chunk,
                )
            )

        try:

            self.client.upsert(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points=points,
            )

            logger.info(
                f"Successfully indexed {len(points)} chunks into Qdrant."
            )

            # Release temporary memory
            del embeddings
            del points
            del texts

            gc.collect()

            return True

        except Exception as e:

            logger.error(
                f"Failed to upsert chunks to Qdrant: {e}"
            )

            return False

    def search(
        self,
        query: str,
        user_roles: List[str],
        department: str,
        top_k: int = 25,
    ) -> List[Dict[str, Any]]:

        query_vector = Embedder.embed_query(query)

        # Security & RBAC payload filtering
        allowed_access_levels = [
            "public",
            "employee",
        ]

        roles_lower = [
            r.lower()
            for r in user_roles
        ]

        if "admin" in roles_lower:
            allowed_access_levels.extend(
                [
                    "hr",
                    "finance",
                    "engineering",
                    "admin",
                    "confidential",
                ]
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
                    limit=top_k,
                )

                results = res_obj.points

            elif hasattr(self.client, "search"):

                results = self.client.search(
                    collection_name=settings.QDRANT_COLLECTION_NAME,
                    query_vector=query_vector,
                    limit=top_k,
                )

            else:

                logger.error(
                    "Qdrant client has no supported search method."
                )

                return []

        except Exception as e:

            logger.error(
                f"Dense vector search failed: {e}"
            )

            return []

        hits = []

        for res in results:

            payload = res.payload or {}

            acc = payload.get(
                "access_level",
                "employee",
            ).lower()

            doc_dept = payload.get(
                "department",
                "General",
            )

            # RBAC Verification
            if (
                acc not in allowed_access_levels
                and doc_dept != department
                and "admin" not in roles_lower
            ):
                continue

            hits.append(
                {
                    "chunk_id": str(res.id),
                    "document_id": payload.get(
                        "document_id"
                    ),
                    "document_name": payload.get(
                        "document_name"
                    ),
                    "text": payload.get("text"),
                    "page_number": payload.get(
                        "page_number",
                        1,
                    ),
                    "section_title": payload.get(
                        "section_title",
                        "General",
                    ),
                    "department": payload.get(
                        "department",
                        "General",
                    ),
                    "access_level": payload.get(
                        "access_level",
                        "employee",
                    ),
                    "score": float(res.score),
                    "dense_score": float(res.score),
                }
            )

        return hits

    def delete_document_chunks(
        self,
        document_id: str
    ):

        try:

            self.client.delete(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(
                                value=document_id
                            ),
                        )
                    ]
                ),
            )

        except Exception as e:

            logger.error(
                f"Error deleting Qdrant chunks "
                f"for document {document_id}: {e}"
            )


# Global Qdrant store
qdrant_store = QdrantDenseStore()