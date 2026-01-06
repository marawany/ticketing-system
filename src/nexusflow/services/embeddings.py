"""
Embedding Service

Handles text embedding generation using OpenAI/Azure OpenAI models.
"""

import structlog
from openai import AsyncOpenAI

from nexusflow.config import settings

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings.

    Uses OpenAI's text-embedding models for vectorizing ticket content.
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
    ):
        self.api_key = api_key or settings.openai_api_key
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.embedding_model
        self.dimension = settings.embedding_dimension

        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        """Get or create the OpenAI client."""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding
        """
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.model,
            )
            embedding = response.data[0].embedding
            logger.debug("Generated embedding", text_length=len(text), dim=len(embedding))
            return embedding
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=self.model,
            )
            embeddings = [item.embedding for item in response.data]
            logger.debug("Generated embeddings batch", count=len(texts))
            return embeddings
        except Exception as e:
            logger.error("Batch embedding generation failed", error=str(e))
            raise

    async def embed_ticket(self, title: str, description: str) -> list[float]:
        """
        Generate embedding for a ticket.

        Combines title and description for embedding.
        """
        text = f"{title}\n\n{description}"
        return await self.embed_text(text)

    async def get_embedding(self, text: str) -> list[float]:
        """
        Alias for embed_text for simpler API.

        Args:
            text: The text to embed

        Returns:
            List of floats representing the embedding
        """
        return await self.embed_text(text)


# Singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
