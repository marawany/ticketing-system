"""
Milvus Vector Database Client

Manages vector embeddings for ticket similarity search.
Used in conjunction with graph-based classification for ensemble confidence.
"""

from typing import Any

import structlog
from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)
from pymilvus import (
    MilvusClient as PyMilvusClient,
)

from nexusflow.config import settings

logger = structlog.get_logger(__name__)


class MilvusClient:
    """
    Milvus client for managing ticket embeddings and similarity search.

    Collection Schema:
    - id: VARCHAR (ticket UUID)
    - embedding: FLOAT_VECTOR (dimension based on embedding model)
    - title: VARCHAR (for result display)
    - level1_category: VARCHAR
    - level2_category: VARCHAR
    - level3_category: VARCHAR
    - was_correct: BOOL (for weighted similarity)
    - created_at: INT64 (timestamp)
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        collection_name: str = None,
    ):
        self.host = host or settings.milvus_host
        self.port = port or settings.milvus_port
        self.user = user or settings.milvus_user
        self.password = password or settings.milvus_password
        self.collection_name = collection_name or settings.milvus_collection
        self.embedding_dim = settings.embedding_dimension

        self._client: PyMilvusClient | None = None
        self._collection: Collection | None = None

    def connect(self) -> None:
        """Establish connection to Milvus."""
        try:
            # Connect using the new PyMilvusClient
            uri = f"http://{self.host}:{self.port}"
            self._client = PyMilvusClient(
                uri=uri,
                user=self.user,
                password=self.password,
            )

            # Also establish legacy connection for Collection operations
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
            )

            logger.info("Connected to Milvus", host=self.host, port=self.port)
        except Exception as e:
            logger.error("Failed to connect to Milvus", error=str(e))
            raise

    def close(self) -> None:
        """Close the Milvus connection."""
        if self._client:
            self._client.close()
            self._client = None
        connections.disconnect("default")
        logger.info("Milvus connection closed")

    def _ensure_connected(self) -> None:
        """Ensure connection is established."""
        if self._client is None:
            self.connect()

    # =========================================================================
    # Collection Management
    # =========================================================================

    def create_collection(self, drop_existing: bool = False) -> None:
        """Create the tickets collection with proper schema."""
        self._ensure_connected()

        # Check if collection exists
        if utility.has_collection(self.collection_name):
            if drop_existing:
                utility.drop_collection(self.collection_name)
                logger.info("Dropped existing collection", name=self.collection_name)
            else:
                logger.info("Collection already exists", name=self.collection_name)
                self._collection = Collection(self.collection_name)
                return

        # Define schema
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=36, is_primary=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
            FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="description_snippet", dtype=DataType.VARCHAR, max_length=1000),
            FieldSchema(name="level1_category", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="level2_category", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="level3_category", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="was_correct", dtype=DataType.BOOL),
            FieldSchema(name="confidence", dtype=DataType.FLOAT),
            FieldSchema(name="created_at", dtype=DataType.INT64),
        ]

        schema = CollectionSchema(
            fields=fields,
            description="NexusFlow ticket embeddings for similarity search",
        )

        # Create collection
        self._collection = Collection(
            name=self.collection_name,
            schema=schema,
            using="default",
        )

        # Create index for vector search
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        }
        self._collection.create_index(
            field_name="embedding",
            index_params=index_params,
        )

        logger.info("Created collection with index", name=self.collection_name)

    def get_collection(self) -> Collection:
        """Get the collection object."""
        self._ensure_connected()
        if self._collection is None:
            if utility.has_collection(self.collection_name):
                self._collection = Collection(self.collection_name)
            else:
                self.create_collection()
        return self._collection

    def load_collection(self) -> None:
        """Load collection into memory for search."""
        collection = self.get_collection()
        collection.load()
        logger.info("Collection loaded into memory", name=self.collection_name)

    def release_collection(self) -> None:
        """Release collection from memory."""
        collection = self.get_collection()
        collection.release()
        logger.info("Collection released from memory", name=self.collection_name)

    # =========================================================================
    # Insert Operations
    # =========================================================================

    def insert_ticket(
        self,
        ticket_id: str,
        embedding: list[float],
        title: str,
        description: str,
        level1_category: str,
        level2_category: str,
        level3_category: str,
        was_correct: bool = True,
        confidence: float = 1.0,
        created_at: int = None,
    ) -> None:
        """Insert a single ticket embedding."""
        self._ensure_connected()

        data = [
            {
                "id": ticket_id,
                "embedding": embedding,
                "title": title[:500],
                "description_snippet": description[:1000],
                "level1_category": level1_category,
                "level2_category": level2_category,
                "level3_category": level3_category,
                "was_correct": was_correct,
                "confidence": confidence,
                "created_at": created_at or int(__import__("time").time()),
            }
        ]

        collection = self.get_collection()
        collection.insert(data)
        collection.flush()

        logger.debug("Inserted ticket embedding", ticket_id=ticket_id)

    def insert_tickets_batch(
        self,
        tickets: list[dict[str, Any]],
    ) -> int:
        """
        Insert a batch of ticket embeddings.

        Each ticket dict should contain:
        - id, embedding, title, description, level1_category, level2_category,
          level3_category, was_correct (optional), confidence (optional), created_at (optional)
        """
        self._ensure_connected()

        import time

        current_time = int(time.time())

        data = []
        for ticket in tickets:
            data.append(
                {
                    "id": ticket["id"],
                    "embedding": ticket["embedding"],
                    "title": ticket.get("title", "")[:500],
                    "description_snippet": ticket.get("description", "")[:1000],
                    "level1_category": ticket["level1_category"],
                    "level2_category": ticket["level2_category"],
                    "level3_category": ticket["level3_category"],
                    "was_correct": ticket.get("was_correct", True),
                    "confidence": ticket.get("confidence", 1.0),
                    "created_at": ticket.get("created_at", current_time),
                }
            )

        collection = self.get_collection()
        collection.insert(data)
        collection.flush()

        logger.info("Inserted batch of tickets", count=len(tickets))
        return len(tickets)

    # =========================================================================
    # Search Operations
    # =========================================================================

    def search_similar(
        self,
        query_embedding: list[float],
        limit: int = 10,
        min_score: float = 0.0,
        filter_expr: str = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar tickets using vector similarity.

        Args:
            query_embedding: The embedding vector to search with
            limit: Maximum number of results
            min_score: Minimum similarity score (0-1 for cosine)
            filter_expr: Optional Milvus filter expression

        Returns:
            List of matching tickets with similarity scores
        """
        self._ensure_connected()

        collection = self.get_collection()
        collection.load()

        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 16},
        }

        output_fields = [
            "id",
            "title",
            "description_snippet",
            "level1_category",
            "level2_category",
            "level3_category",
            "was_correct",
            "confidence",
        ]

        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=limit,
            expr=filter_expr,
            output_fields=output_fields,
        )

        matches = []
        for hits in results:
            for hit in hits:
                # Cosine similarity is already 0-1
                similarity = (
                    hit.score if hit.score >= 0 else 1 + hit.score
                )  # Handle negative distances

                if similarity >= min_score:
                    matches.append(
                        {
                            "ticket_id": hit.entity.get("id"),
                            "title": hit.entity.get("title"),
                            "description_snippet": hit.entity.get("description_snippet"),
                            "level1_category": hit.entity.get("level1_category"),
                            "level2_category": hit.entity.get("level2_category"),
                            "level3_category": hit.entity.get("level3_category"),
                            "was_correct": hit.entity.get("was_correct"),
                            "confidence": hit.entity.get("confidence"),
                            "similarity_score": similarity,
                        }
                    )

        return matches

    def search_by_category(
        self,
        query_embedding: list[float],
        level1: str = None,
        level2: str = None,
        level3: str = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search within a specific category."""
        filters = []
        if level1:
            filters.append(f'level1_category == "{level1}"')
        if level2:
            filters.append(f'level2_category == "{level2}"')
        if level3:
            filters.append(f'level3_category == "{level3}"')

        filter_expr = " && ".join(filters) if filters else None
        return self.search_similar(query_embedding, limit=limit, filter_expr=filter_expr)

    def get_classification_confidence(
        self,
        query_embedding: list[float],
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        Get classification confidence based on similar tickets.

        Returns confidence scores based on:
        - Category agreement among similar tickets
        - Weighted by similarity scores
        - Weighted by whether similar tickets were correctly classified
        """
        matches = self.search_similar(query_embedding, limit=limit)

        if not matches:
            return {
                "level1": None,
                "level2": None,
                "level3": None,
                "confidence": 0.0,
                "match_count": 0,
                "category_votes": {},
            }

        # Aggregate votes for each category level
        level1_votes: dict[str, float] = {}
        level2_votes: dict[str, float] = {}
        level3_votes: dict[str, float] = {}

        for match in matches:
            # Weight by similarity and correctness
            weight = match["similarity_score"]
            if match.get("was_correct") is False:
                weight *= 0.5  # Reduce weight of incorrectly classified tickets

            l1 = match["level1_category"]
            l2 = match["level2_category"]
            l3 = match["level3_category"]

            level1_votes[l1] = level1_votes.get(l1, 0) + weight
            level2_votes[l2] = level2_votes.get(l2, 0) + weight
            level3_votes[l3] = level3_votes.get(l3, 0) + weight

        # Normalize votes
        def normalize_votes(votes: dict[str, float]) -> dict[str, float]:
            total = sum(votes.values())
            if total == 0:
                return votes
            return {k: v / total for k, v in votes.items()}

        level1_norm = normalize_votes(level1_votes)
        level2_norm = normalize_votes(level2_votes)
        level3_norm = normalize_votes(level3_votes)

        # Get top prediction for each level
        top_l1 = max(level1_norm.items(), key=lambda x: x[1]) if level1_norm else (None, 0)
        top_l2 = max(level2_norm.items(), key=lambda x: x[1]) if level2_norm else (None, 0)
        top_l3 = max(level3_norm.items(), key=lambda x: x[1]) if level3_norm else (None, 0)

        # Calculate overall confidence
        confidence = (top_l1[1] + top_l2[1] + top_l3[1]) / 3

        return {
            "level1": top_l1[0],
            "level2": top_l2[0],
            "level3": top_l3[0],
            "confidence": confidence,
            "level1_confidence": top_l1[1],
            "level2_confidence": top_l2[1],
            "level3_confidence": top_l3[1],
            "match_count": len(matches),
            "category_votes": {
                "level1": level1_norm,
                "level2": level2_norm,
                "level3": level3_norm,
            },
        }

    # =========================================================================
    # Update Operations
    # =========================================================================

    def update_ticket_correctness(
        self,
        ticket_id: str,
        was_correct: bool,
    ) -> None:
        """Update the correctness flag for a ticket after HITL review."""
        self._ensure_connected()

        # Milvus doesn't support direct updates, so we need to delete and re-insert
        # For production, consider using a separate metadata store
        collection = self.get_collection()

        # Get existing data
        results = collection.query(
            expr=f'id == "{ticket_id}"',
            output_fields=["*"],
        )

        if results:
            ticket_data = results[0]
            collection.delete(expr=f'id == "{ticket_id}"')

            # Re-insert with updated correctness
            ticket_data["was_correct"] = was_correct
            collection.insert([ticket_data])
            collection.flush()

            logger.info("Updated ticket correctness", ticket_id=ticket_id, was_correct=was_correct)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_collection_stats(self) -> dict[str, Any]:
        """Get statistics about the collection."""
        self._ensure_connected()

        collection = self.get_collection()
        stats = {
            "name": self.collection_name,
            "num_entities": collection.num_entities,
            "has_index": collection.has_index(),
        }

        return stats

    def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Search for similar tickets (simplified interface).

        Returns list of dicts with ticket_id, score, and metadata.
        """
        matches = self.search_similar(query_embedding, limit=limit)

        # Reformat for simpler output
        results = []
        for match in matches:
            results.append(
                {
                    "ticket_id": match["ticket_id"],
                    "score": match["similarity_score"],
                    "metadata": {
                        "title": match["title"],
                        "level1": match["level1_category"],
                        "level2": match["level2_category"],
                        "level3": match["level3_category"],
                        "category": f"{match['level1_category']} > {match['level2_category']} > {match['level3_category']}",
                    },
                }
            )

        return results

    def insert(
        self,
        ticket_id: str,
        embedding: list[float],
        metadata: dict[str, Any],
    ) -> None:
        """
        Insert a single ticket embedding (simplified interface).
        """
        self.insert_ticket(
            ticket_id=ticket_id,
            embedding=embedding,
            title=metadata.get("title", "")[:500],
            description=metadata.get("description", "")[:1000] if "description" in metadata else "",
            level1_category=metadata.get("level1", ""),
            level2_category=metadata.get("level2", ""),
            level3_category=metadata.get("level3", ""),
            was_correct=metadata.get("was_correct", True),
            confidence=metadata.get("confidence", 1.0),
        )


# Singleton instance
_milvus_client: MilvusClient | None = None


def get_milvus_client() -> MilvusClient:
    """Get or create the Milvus client singleton."""
    global _milvus_client
    if _milvus_client is None:
        _milvus_client = MilvusClient()
        _milvus_client.connect()
    return _milvus_client


def close_milvus_client() -> None:
    """Close the Milvus client."""
    global _milvus_client
    if _milvus_client:
        _milvus_client.close()
        _milvus_client = None
