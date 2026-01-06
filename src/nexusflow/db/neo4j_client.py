"""
Neo4j Graph Database Client

Manages the classification hierarchy graph and ticket relationships.
The graph structure supports 3-level classification with weighted edges
based on historical accuracy.
"""

import json
from contextlib import asynccontextmanager
from typing import Any

import structlog
from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession
from neo4j.exceptions import AuthError, ServiceUnavailable

from nexusflow.config import settings

logger = structlog.get_logger(__name__)


class Neo4jClient:
    """
    Neo4j client for managing the classification graph.

    Graph Structure:
    - Level1Category nodes (e.g., "Technical Support")
    - Level2Category nodes (e.g., "Authentication")
    - Level3Category nodes (e.g., "Password Reset Issues")
    - CONTAINS relationships between levels
    - Ticket nodes linked to Level3 categories
    """

    def __init__(
        self,
        uri: str = None,
        user: str = None,
        password: str = None,
        database: str = None,
    ):
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        self.database = database or settings.neo4j_database
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Establish connection to Neo4j."""
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=3600,
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info("Connected to Neo4j", uri=self.uri, database=self.database)
        except AuthError as e:
            logger.error("Neo4j authentication failed", error=str(e))
            raise
        except ServiceUnavailable as e:
            logger.error("Neo4j service unavailable", error=str(e))
            raise

    async def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    @asynccontextmanager
    async def session(self) -> AsyncSession:
        """Get a database session."""
        if not self._driver:
            await self.connect()
        session = self._driver.session(database=self.database)
        try:
            yield session
        finally:
            await session.close()

    # =========================================================================
    # Schema Management
    # =========================================================================

    async def create_schema(self) -> None:
        """Create indexes and constraints for the graph."""
        async with self.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT level1_name IF NOT EXISTS FOR (n:Level1Category) REQUIRE n.name IS UNIQUE",
                "CREATE CONSTRAINT level2_name IF NOT EXISTS FOR (n:Level2Category) REQUIRE n.name IS UNIQUE",
                "CREATE CONSTRAINT level3_name IF NOT EXISTS FOR (n:Level3Category) REQUIRE n.name IS UNIQUE",
                "CREATE CONSTRAINT ticket_id IF NOT EXISTS FOR (n:Ticket) REQUIRE n.id IS UNIQUE",
            ]

            # Create indexes
            indexes = [
                "CREATE INDEX level1_tickets IF NOT EXISTS FOR (n:Level1Category) ON (n.ticket_count)",
                "CREATE INDEX level2_tickets IF NOT EXISTS FOR (n:Level2Category) ON (n.ticket_count)",
                "CREATE INDEX level3_tickets IF NOT EXISTS FOR (n:Level3Category) ON (n.ticket_count)",
                "CREATE INDEX ticket_created IF NOT EXISTS FOR (n:Ticket) ON (n.created_at)",
            ]

            for query in constraints + indexes:
                try:
                    await session.run(query)
                except Exception as e:
                    logger.warning(
                        "Schema query failed (may already exist)", query=query, error=str(e)
                    )

            logger.info("Neo4j schema created/verified")

    # =========================================================================
    # Hierarchy Management
    # =========================================================================

    async def load_hierarchy(self, hierarchy: dict[str, Any]) -> None:
        """
        Load the classification hierarchy into Neo4j.

        Args:
            hierarchy: Dict with 'categories' key containing the hierarchy structure
        """
        categories = hierarchy.get("categories", hierarchy)

        async with self.session() as session:
            # Clear existing hierarchy (optional - be careful in production)
            # await session.run("MATCH (n) WHERE n:Level1Category OR n:Level2Category OR n:Level3Category DETACH DELETE n")

            for level1_name, level2_dict in categories.items():
                # Create Level 1 node
                await session.run(
                    """
                    MERGE (l1:Level1Category {name: $name})
                    ON CREATE SET l1.created_at = datetime(), l1.ticket_count = 0, l1.accuracy = 1.0
                    """,
                    name=level1_name,
                )

                for level2_name, level3_list in level2_dict.items():
                    # Create Level 2 node and relationship
                    await session.run(
                        """
                        MATCH (l1:Level1Category {name: $l1_name})
                        MERGE (l2:Level2Category {name: $l2_name})
                        ON CREATE SET l2.created_at = datetime(), l2.ticket_count = 0, l2.accuracy = 1.0
                        MERGE (l1)-[r:CONTAINS]->(l2)
                        ON CREATE SET r.weight = 1.0, r.traversal_count = 0
                        """,
                        l1_name=level1_name,
                        l2_name=level2_name,
                    )

                    for level3_name in level3_list:
                        # Create Level 3 node and relationship
                        await session.run(
                            """
                            MATCH (l2:Level2Category {name: $l2_name})
                            MERGE (l3:Level3Category {name: $l3_name})
                            ON CREATE SET l3.created_at = datetime(), l3.ticket_count = 0,
                                         l3.accuracy = 1.0, l3.description = ''
                            MERGE (l2)-[r:CONTAINS]->(l3)
                            ON CREATE SET r.weight = 1.0, r.traversal_count = 0
                            """,
                            l2_name=level2_name,
                            l3_name=level3_name,
                        )

            logger.info(
                "Hierarchy loaded into Neo4j",
                level1_count=len(categories),
                level2_count=sum(len(v) for v in categories.values()),
            )

    async def load_hierarchy_from_file(self, filepath: str) -> None:
        """Load hierarchy from a JSON file."""
        with open(filepath) as f:
            hierarchy = json.load(f)
        await self.load_hierarchy(hierarchy)

    # =========================================================================
    # Graph Traversal for Classification
    # =========================================================================

    async def get_classification_path(
        self,
        ticket_text: str,
        keywords: list[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Find the best classification path based on keyword matching
        and historical accuracy.

        Returns top matching paths with confidence scores.
        """
        async with self.session() as session:
            # Query for paths that match keywords
            query = """
            MATCH path = (l1:Level1Category)-[r1:CONTAINS]->(l2:Level2Category)-[r2:CONTAINS]->(l3:Level3Category)
            WITH l1, l2, l3, r1, r2,
                 // Calculate keyword match score
                 CASE WHEN $keywords IS NULL OR size($keywords) = 0 THEN 0.5
                      ELSE toFloat(size([k IN $keywords WHERE
                           toLower(l1.name) CONTAINS toLower(k) OR
                           toLower(l2.name) CONTAINS toLower(k) OR
                           toLower(l3.name) CONTAINS toLower(k)])) / size($keywords)
                 END AS keyword_score,
                 // Historical accuracy score
                 (l1.accuracy + l2.accuracy + l3.accuracy) / 3.0 AS accuracy_score,
                 // Edge weights
                 (r1.weight + r2.weight) / 2.0 AS edge_weight
            // Combine scores
            WITH l1, l2, l3,
                 keyword_score * 0.4 + accuracy_score * 0.3 + edge_weight * 0.3 AS combined_score
            WHERE combined_score > 0.1
            RETURN l1.name AS level1, l2.name AS level2, l3.name AS level3,
                   combined_score AS confidence,
                   l3.ticket_count AS historical_count,
                   l3.accuracy AS historical_accuracy
            ORDER BY combined_score DESC
            LIMIT 5
            """

            result = await session.run(query, keywords=keywords or [])
            paths = []
            async for record in result:
                paths.append(
                    {
                        "level1": record["level1"],
                        "level2": record["level2"],
                        "level3": record["level3"],
                        "confidence": record["confidence"],
                        "historical_count": record["historical_count"],
                        "historical_accuracy": record["historical_accuracy"],
                    }
                )

            return paths

    async def get_all_paths(self) -> list[dict[str, Any]]:
        """Get all classification paths in the hierarchy."""
        async with self.session() as session:
            query = """
            MATCH (l1:Level1Category)-[:CONTAINS]->(l2:Level2Category)-[:CONTAINS]->(l3:Level3Category)
            RETURN l1.name AS level1, l2.name AS level2, l3.name AS level3,
                   l3.ticket_count AS ticket_count, l3.accuracy AS accuracy
            ORDER BY l1.name, l2.name, l3.name
            """
            result = await session.run(query)
            paths = []
            async for record in result:
                paths.append(
                    {
                        "level1": record["level1"],
                        "level2": record["level2"],
                        "level3": record["level3"],
                        "ticket_count": record["ticket_count"] or 0,
                        "accuracy": record["accuracy"] or 1.0,
                    }
                )
            return paths

    async def traverse_from_level1(self, level1: str) -> list[dict[str, Any]]:
        """Get all paths starting from a Level 1 category."""
        async with self.session() as session:
            query = """
            MATCH (l1:Level1Category {name: $level1})-[r1:CONTAINS]->(l2:Level2Category)-[r2:CONTAINS]->(l3:Level3Category)
            RETURN l2.name AS level2, l3.name AS level3,
                   r1.weight AS l1_l2_weight, r2.weight AS l2_l3_weight,
                   l3.ticket_count AS ticket_count
            ORDER BY l3.ticket_count DESC
            """
            result = await session.run(query, level1=level1)
            paths = []
            async for record in result:
                paths.append(
                    {
                        "level2": record["level2"],
                        "level3": record["level3"],
                        "weight": (record["l1_l2_weight"] + record["l2_l3_weight"]) / 2,
                        "ticket_count": record["ticket_count"] or 0,
                    }
                )
            return paths

    # =========================================================================
    # Update Operations (for HITL corrections and learning)
    # =========================================================================

    async def update_edge_weight(
        self,
        from_level: str,
        to_level: str,
        from_name: str,
        to_name: str,
        weight_delta: float,
    ) -> None:
        """Update edge weight based on classification feedback."""
        async with self.session() as session:
            query = f"""
            MATCH (from:{from_level} {{name: $from_name}})-[r:CONTAINS]->(to:{to_level} {{name: $to_name}})
            SET r.weight = CASE
                WHEN r.weight + $delta > 2.0 THEN 2.0
                WHEN r.weight + $delta < 0.1 THEN 0.1
                ELSE r.weight + $delta
            END,
            r.traversal_count = r.traversal_count + 1,
            r.last_updated = datetime()
            """
            await session.run(
                query,
                from_name=from_name,
                to_name=to_name,
                delta=weight_delta,
            )

    async def update_category_accuracy(
        self,
        level: str,
        name: str,
        was_correct: bool,
    ) -> None:
        """Update category accuracy based on HITL feedback."""
        async with self.session() as session:
            # Use exponential moving average for accuracy
            alpha = 0.1  # Learning rate
            query = f"""
            MATCH (n:{level} {{name: $name}})
            SET n.accuracy = n.accuracy * (1 - $alpha) + $correct * $alpha,
                n.ticket_count = n.ticket_count + 1,
                n.last_updated = datetime()
            """
            await session.run(
                query,
                name=name,
                alpha=alpha,
                correct=1.0 if was_correct else 0.0,
            )

    async def record_correction(
        self,
        ticket_id: str,
        original_path: tuple[str, str, str],
        corrected_path: tuple[str, str, str],
    ) -> None:
        """Record a HITL correction and update graph weights."""
        # Decrease weights for wrong path
        if original_path[0] != corrected_path[0]:
            await self.update_edge_weight(
                "Level1Category", "Level2Category", original_path[0], original_path[1], -0.1
            )
        if original_path[1] != corrected_path[1]:
            await self.update_edge_weight(
                "Level2Category", "Level3Category", original_path[1], original_path[2], -0.1
            )

        # Increase weights for correct path
        await self.update_edge_weight(
            "Level1Category", "Level2Category", corrected_path[0], corrected_path[1], 0.1
        )
        await self.update_edge_weight(
            "Level2Category", "Level3Category", corrected_path[1], corrected_path[2], 0.1
        )

        # Update accuracy scores
        await self.update_category_accuracy("Level3Category", original_path[2], False)
        await self.update_category_accuracy("Level3Category", corrected_path[2], True)

        logger.info(
            "Recorded correction in graph",
            ticket_id=ticket_id,
            original=original_path,
            corrected=corrected_path,
        )

    # =========================================================================
    # Ticket Operations
    # =========================================================================

    async def add_ticket_to_graph(
        self,
        ticket_id: str,
        level3_category: str,
        confidence: float,
    ) -> None:
        """Add a ticket node and link to its classification."""
        async with self.session() as session:
            query = """
            MATCH (l3:Level3Category {name: $category})
            MERGE (t:Ticket {id: $ticket_id})
            ON CREATE SET t.created_at = datetime(), t.confidence = $confidence
            MERGE (t)-[r:CLASSIFIED_AS]->(l3)
            ON CREATE SET r.confidence = $confidence, r.created_at = datetime()
            SET l3.ticket_count = l3.ticket_count + 1
            """
            await session.run(
                query,
                ticket_id=ticket_id,
                category=level3_category,
                confidence=confidence,
            )

    async def get_similar_tickets_by_category(
        self,
        level3_category: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Get recent tickets in the same category."""
        async with self.session() as session:
            query = """
            MATCH (t:Ticket)-[:CLASSIFIED_AS]->(l3:Level3Category {name: $category})
            RETURN t.id AS ticket_id, t.created_at AS created_at, t.confidence AS confidence
            ORDER BY t.created_at DESC
            LIMIT $limit
            """
            result = await session.run(query, category=level3_category, limit=limit)
            tickets = []
            async for record in result:
                tickets.append(
                    {
                        "ticket_id": record["ticket_id"],
                        "created_at": str(record["created_at"]),
                        "confidence": record["confidence"],
                    }
                )
            return tickets

    # =========================================================================
    # Analytics
    # =========================================================================

    async def get_graph_statistics(self) -> dict[str, Any]:
        """Get statistics about the classification graph."""
        async with self.session() as session:
            query = """
            MATCH (l1:Level1Category)
            WITH count(l1) AS level1_count
            MATCH (l2:Level2Category)
            WITH level1_count, count(l2) AS level2_count
            MATCH (l3:Level3Category)
            WITH level1_count, level2_count, count(l3) AS level3_count
            MATCH (t:Ticket)
            RETURN level1_count, level2_count, level3_count, count(t) AS ticket_count
            """
            result = await session.run(query)
            record = await result.single()

            if record:
                return {
                    "level1_categories": record["level1_count"],
                    "level2_categories": record["level2_count"],
                    "level3_categories": record["level3_count"],
                    "total_tickets": record["ticket_count"],
                }
            return {
                "level1_categories": 0,
                "level2_categories": 0,
                "level3_categories": 0,
                "total_tickets": 0,
            }

    async def record_classification(
        self,
        ticket_id: str,
        level1: str,
        level2: str,
        level3: str,
        was_corrected: bool = False,
    ) -> None:
        """
        Record a classification result in the graph.
        Updates category statistics and creates ticket node.
        """
        async with self.session():
            # Create ticket node and link to category
            await self.add_ticket_to_graph(ticket_id, level3, 1.0 if not was_corrected else 0.8)

            # Update category accuracy based on correction
            if was_corrected:
                await self.update_category_accuracy("Level3Category", level3, True)

            # Update edge weights (reinforce used path)
            await self.update_edge_weight("Level1Category", "Level2Category", level1, level2, 0.05)
            await self.update_edge_weight("Level2Category", "Level3Category", level2, level3, 0.05)

            logger.debug(
                "Recorded classification",
                ticket_id=ticket_id,
                path=f"{level1} > {level2} > {level3}",
                was_corrected=was_corrected,
            )

    async def find_matching_categories(
        self,
        text: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Find matching categories based on text content.
        Simple text matching with scoring.
        """
        # Extract words from text
        import re

        words = re.findall(r"\w+", text.lower())
        keywords = list(set(words))[:20]  # Take first 20 unique words

        return await self.get_classification_path(text, keywords)

    async def get_category_distribution(self) -> list[dict[str, Any]]:
        """Get ticket distribution across categories."""
        async with self.session() as session:
            query = """
            MATCH (l1:Level1Category)-[:CONTAINS]->(l2:Level2Category)-[:CONTAINS]->(l3:Level3Category)
            RETURN l1.name AS level1, l2.name AS level2, l3.name AS level3,
                   l3.ticket_count AS count, l3.accuracy AS accuracy
            ORDER BY l3.ticket_count DESC
            """
            result = await session.run(query)
            distribution = []
            async for record in result:
                distribution.append(
                    {
                        "level1": record["level1"],
                        "level2": record["level2"],
                        "level3": record["level3"],
                        "count": record["count"] or 0,
                        "accuracy": record["accuracy"] or 1.0,
                    }
                )
            return distribution


# Singleton instance
_neo4j_client: Neo4jClient | None = None


async def get_neo4j_client() -> Neo4jClient:
    """Get or create the Neo4j client singleton."""
    global _neo4j_client
    if _neo4j_client is None:
        _neo4j_client = Neo4jClient()
        await _neo4j_client.connect()
    return _neo4j_client


async def close_neo4j_client() -> None:
    """Close the Neo4j client."""
    global _neo4j_client
    if _neo4j_client:
        await _neo4j_client.close()
        _neo4j_client = None
