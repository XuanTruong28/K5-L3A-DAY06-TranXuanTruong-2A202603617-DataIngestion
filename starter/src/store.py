"""Store and search vectors using ChromaDB persistent local store."""
from pathlib import Path
from typing import Any
import chromadb
from .models import Chunk


class PgVectorStore:
    """Vector store adapter implementing persistence, cosine search, and metadata filter."""

    def __init__(self, database_url: str = "starter/results/chroma", dimensions: int = 384) -> None:
        self.dimensions = dimensions
        self.storage_path = Path(database_url)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.storage_path))
        self.collections: dict[str, Any] = {}

    def create_schema(self) -> None:
        """Create collections for strategies and configure cosine distance."""
        for strategy in ["strategy_A", "strategy_B", "strategy_C"]:
            # Dùng cosine distance cho phép đo tương đồng góc
            self.collections[strategy] = self.client.get_or_create_collection(
                name=strategy,
                metadata={"hnsw:space": "cosine"}
            )

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """Validate lengths and write stable IDs without duplicates."""
        if len(chunks) != len(vectors):
            raise ValueError(f"Mismatch: {len(chunks)} chunks vs {len(vectors)} vectors")

        col_name = f"strategy_{strategy}" if not strategy.startswith("strategy_") else strategy
        col = self.client.get_or_create_collection(name=col_name, metadata={"hnsw:space": "cosine"})
        self.collections[col_name] = col

        if not chunks:
            return

        ids = [c.chunk_id for c in chunks]
        texts = [c.text for c in chunks]
        metadatas = [
            {
                "document_id": c.document_id,
                "source": c.source,
                "page": int(c.page),
                "chapter": str(c.metadata.get("chapter", "")),
                "category": str(c.metadata.get("category", "")),
                "strategy": str(c.metadata.get("strategy", strategy))
            }
            for c in chunks
        ]

        # Chia batch nhỏ để nạp an toàn
        batch_size = 200
        for i in range(0, len(ids), batch_size):
            end = i + batch_size
            col.upsert(
                ids=ids[i:end],
                documents=texts[i:end],
                embeddings=vectors[i:end],
                metadatas=metadatas[i:end]
            )

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Filter metadata, rank by cosine similarity, and return top-k."""
        col_name = f"strategy_{strategy}" if not strategy.startswith("strategy_") else strategy
        col = self.collections.get(col_name) or self.client.get_collection(name=col_name)

        where_clause = None
        if filters:
            # ChromaDB filter định dạng {"key": "value"}
            where_clause = {k: v for k, v in filters.items()}

        results = col.query(
            query_embeddings=[query_vector],
            n_results=top_k,
            where=where_clause
        )

        hits: list[dict[str, Any]] = []
        if not results or not results["ids"] or not results["ids"][0]:
            return hits

        for idx in range(len(results["ids"][0])):
            distance = results["distances"][0][idx] if results.get("distances") else 0.0
            # Cosine similarity = 1 - cosine distance
            score = round(1.0 - distance, 4)
            meta = results["metadatas"][0][idx]
            hits.append({
                "chunk_id": results["ids"][0][idx],
                "text": results["documents"][0][idx],
                "score": score,
                "page": meta.get("page"),
                "source": meta.get("source"),
                "metadata": meta
            })

        return hits


# Alias để tương thích cả 2 tên gọi
ChromaVectorStore = PgVectorStore
