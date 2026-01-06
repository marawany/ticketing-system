#!/usr/bin/env python3
"""
Load Real Data into NexusFlow

This script:
1. Analyzes the gold.csv dataset
2. Builds a sophisticated multi-dimensional graph in Neo4j
3. Creates embeddings and loads them into Milvus
4. Tracks statistics for confidence calibration
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import structlog
from tqdm import tqdm

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nexusflow.config import settings
from nexusflow.db.neo4j_client import Neo4jClient
from nexusflow.db.milvus_client import MilvusClient

logger = structlog.get_logger(__name__)


class RealDataLoader:
    """Loads real data into Neo4j and Milvus."""
    
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df = None
        self.neo4j: Neo4jClient = None
        self.milvus: MilvusClient = None
        
    async def connect(self):
        """Connect to databases."""
        logger.info("Connecting to Neo4j...")
        self.neo4j = Neo4jClient()
        await self.neo4j.connect()
        
        # Milvus is optional - skip if not available
        try:
            logger.info("Connecting to Milvus...")
            self.milvus = MilvusClient()
            self.milvus.connect()  # Sync connect
        except Exception as e:
            logger.warning("Milvus not available, skipping vector DB", error=str(e))
            self.milvus = None
        
    async def close(self):
        """Close database connections."""
        if self.neo4j:
            await self.neo4j.close()
        if self.milvus:
            try:
                self.milvus.close()
            except Exception:
                pass
    
    def load_csv(self):
        """Load and clean CSV data."""
        logger.info("Loading CSV data...", path=self.csv_path)
        self.df = pd.read_csv(self.csv_path)
        
        # Clean data
        self.df['Environment'] = self.df['Environment'].fillna('Unknown').str.strip()
        self.df['Regulatory'] = self.df['Regulatory'].fillna('No').astype(str)
        self.df['Regulatory'] = self.df['Regulatory'].replace({'0': 'No', '1': 'Yes', 'no': 'No', 'yes': 'Yes'})
        
        logger.info("Loaded records", count=len(self.df))
        
        # Print statistics
        print("\n" + "="*60)
        print("DATA ANALYSIS")
        print("="*60)
        print(f"Total tickets: {len(self.df):,}")
        print(f"\nReport Categories (Level 1): {self.df['Report_Category'].nunique()}")
        for cat, count in self.df['Report_Category'].value_counts().items():
            print(f"  - {cat}: {count:,}")
        print(f"\nProducts (Level 2): {self.df['Product'].nunique()}")
        print(f"Business Units (Level 3): {self.df['BU'].nunique()}")
        print(f"Environments: {self.df['Environment'].nunique()}")
        print("="*60 + "\n")
        
    async def clear_existing_data(self):
        """Clear existing graph data."""
        logger.info("Clearing existing Neo4j data...")
        async with self.neo4j.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
        logger.info("Neo4j cleared")
        
    async def build_graph(self):
        """Build the classification graph from real data."""
        logger.info("Building Neo4j graph...")
        
        # Create constraints first
        await self.neo4j.create_schema()
        
        async with self.neo4j.session() as session:
            # Additional constraints for new node types
            constraints = [
                "CREATE CONSTRAINT bu_name IF NOT EXISTS FOR (n:BusinessUnit) REQUIRE n.name IS UNIQUE",
                "CREATE CONSTRAINT env_name IF NOT EXISTS FOR (n:Environment) REQUIRE n.name IS UNIQUE",
            ]
            for query in constraints:
                try:
                    await session.run(query)
                except Exception:
                    pass
        
        # Group data
        grouped = self.df.groupby(['Report_Category', 'Product', 'BU']).agg({
            'Case_Num': 'count',
            'Environment': lambda x: x.mode().iloc[0] if len(x) > 0 else 'Unknown',
            'Regulatory': lambda x: (x == 'Yes').sum(),
        }).reset_index()
        grouped.columns = ['report_category', 'product', 'bu', 'ticket_count', 'primary_env', 'regulatory_count']
        
        # Calculate accuracy proxy (based on resolution quality if available)
        if 'resolution_quality' in self.df.columns:
            quality_map = self.df.groupby(['Report_Category', 'Product', 'BU'])['resolution_quality'].apply(
                lambda x: (x == 'high').sum() / len(x) if len(x) > 0 else 1.0
            ).to_dict()
        else:
            quality_map = {}
        
        print(f"Creating {len(grouped['report_category'].unique())} Level 1 categories...")
        print(f"Creating {len(grouped['product'].unique())} Level 2 products...")
        print(f"Creating {len(grouped['bu'].unique())} Level 3 business units...")
        
        async with self.neo4j.session() as session:
            # Create Level 1 categories with statistics
            l1_stats = self.df.groupby('Report_Category').agg({
                'Case_Num': 'count',
                'Regulatory': lambda x: (x == 'Yes').sum()
            }).reset_index()
            
            for _, row in tqdm(l1_stats.iterrows(), total=len(l1_stats), desc="Level 1"):
                await session.run("""
                    MERGE (l1:Level1Category {name: $name})
                    SET l1.ticket_count = $count,
                        l1.regulatory_count = $regulatory,
                        l1.accuracy = 1.0,
                        l1.created_at = datetime()
                """, name=row['Report_Category'], count=int(row['Case_Num']), 
                     regulatory=int(row['Regulatory']))
            
            # Create Level 2 products with relationships
            l2_stats = self.df.groupby(['Report_Category', 'Product']).agg({
                'Case_Num': 'count',
                'Regulatory': lambda x: (x == 'Yes').sum()
            }).reset_index()
            
            for _, row in tqdm(l2_stats.iterrows(), total=len(l2_stats), desc="Level 2"):
                await session.run("""
                    MATCH (l1:Level1Category {name: $l1_name})
                    MERGE (l2:Level2Category {name: $name})
                    ON CREATE SET l2.ticket_count = $count,
                                  l2.regulatory_count = $regulatory,
                                  l2.accuracy = 1.0,
                                  l2.created_at = datetime()
                    ON MATCH SET l2.ticket_count = l2.ticket_count + $count
                    MERGE (l1)-[r:CONTAINS]->(l2)
                    ON CREATE SET r.weight = 1.0, r.traversal_count = $count
                    ON MATCH SET r.traversal_count = r.traversal_count + $count
                """, l1_name=row['Report_Category'], name=row['Product'],
                     count=int(row['Case_Num']), regulatory=int(row['Regulatory']))
            
            # Create Level 3 business units with relationships
            for _, row in tqdm(grouped.iterrows(), total=len(grouped), desc="Level 3"):
                accuracy = quality_map.get((row['report_category'], row['product'], row['bu']), 1.0)
                await session.run("""
                    MATCH (l2:Level2Category {name: $l2_name})
                    MERGE (l3:Level3Category {name: $name})
                    ON CREATE SET l3.ticket_count = $count,
                                  l3.regulatory_count = $regulatory,
                                  l3.primary_environment = $env,
                                  l3.accuracy = $accuracy,
                                  l3.created_at = datetime()
                    ON MATCH SET l3.ticket_count = l3.ticket_count + $count
                    MERGE (l2)-[r:CONTAINS]->(l3)
                    ON CREATE SET r.weight = 1.0, r.traversal_count = $count
                    ON MATCH SET r.traversal_count = r.traversal_count + $count
                """, l2_name=row['product'], name=row['bu'],
                     count=int(row['ticket_count']), regulatory=int(row['regulatory_count']),
                     env=row['primary_env'], accuracy=accuracy)
            
            # Create Environment nodes and link to Level 3
            print("\nCreating environment relationships...")
            env_data = self.df.groupby(['BU', 'Environment']).size().reset_index(name='count')
            for _, row in tqdm(env_data.iterrows(), total=len(env_data), desc="Environments"):
                await session.run("""
                    MATCH (l3:Level3Category {name: $bu})
                    MERGE (env:Environment {name: $env_name})
                    MERGE (l3)-[r:OPERATES_IN]->(env)
                    ON CREATE SET r.ticket_count = $count
                    ON MATCH SET r.ticket_count = r.ticket_count + $count
                """, bu=row['BU'], env_name=row['Environment'], count=int(row['count']))
        
        logger.info("Neo4j graph built successfully")
        
    async def create_milvus_collection(self):
        """Create Milvus collection with ticket embeddings."""
        logger.info("Creating Milvus collection...")
        
        # Drop existing collection
        try:
            await self.milvus.drop_collection("nexusflow_real_tickets")
        except Exception:
            pass
        
        # Create new collection
        await self.milvus.create_collection(
            collection_name="nexusflow_real_tickets",
            dimension=settings.embedding_dimension,
        )
        
        logger.info("Milvus collection created")
        
    async def load_embeddings(self, batch_size: int = 100, max_tickets: int = None):
        """Generate and load embeddings for tickets."""
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Select tickets to embed
        tickets = self.df.head(max_tickets) if max_tickets else self.df
        total = len(tickets)
        
        logger.info("Generating embeddings...", total=total)
        
        embedded_count = 0
        for i in tqdm(range(0, total, batch_size), desc="Embedding batches"):
            batch = tickets.iloc[i:i+batch_size]
            
            # Create text for embedding
            texts = []
            metadata = []
            for _, row in batch.iterrows():
                text = f"{row['Inquiry Short Description']} {row.get('synopsis', '')}"
                texts.append(text[:8000])  # Limit text length
                metadata.append({
                    "ticket_id": row['Case_Num'],
                    "category": row['Report_Category'],
                    "product": row['Product'],
                    "bu": row['BU'],
                    "environment": str(row.get('Environment', 'Unknown')),
                    "regulatory": str(row.get('Regulatory', 'No')),
                })
            
            try:
                # Generate embeddings
                response = await client.embeddings.create(
                    model=settings.embedding_model,
                    input=texts
                )
                
                embeddings = [e.embedding for e in response.data]
                
                # Insert into Milvus
                await self.milvus.insert(
                    collection_name="nexusflow_real_tickets",
                    embeddings=embeddings,
                    metadata=metadata
                )
                
                embedded_count += len(embeddings)
                
            except Exception as e:
                logger.warning("Batch embedding failed", error=str(e), batch=i)
                continue
        
        logger.info("Embeddings loaded", count=embedded_count)
        
    async def print_statistics(self):
        """Print final graph statistics."""
        stats = await self.neo4j.get_graph_statistics()
        
        async with self.neo4j.session() as session:
            # Get edge counts
            result = await session.run("""
                MATCH ()-[r:CONTAINS]->()
                RETURN count(r) as contains_edges
            """)
            record = await result.single()
            contains_edges = record["contains_edges"] if record else 0
            
            result = await session.run("""
                MATCH ()-[r:OPERATES_IN]->()
                RETURN count(r) as env_edges
            """)
            record = await result.single()
            env_edges = record["env_edges"] if record else 0
            
            result = await session.run("""
                MATCH (e:Environment)
                RETURN count(e) as env_count
            """)
            record = await result.single()
            env_count = record["env_count"] if record else 0
        
        print("\n" + "="*60)
        print("FINAL GRAPH STATISTICS")
        print("="*60)
        print(f"Level 1 Categories: {stats['level1_categories']}")
        print(f"Level 2 Products: {stats['level2_categories']}")
        print(f"Level 3 Business Units: {stats['level3_categories']}")
        print(f"Environments: {env_count}")
        print(f"CONTAINS edges: {contains_edges}")
        print(f"OPERATES_IN edges: {env_edges}")
        print(f"Total tickets in graph: {stats['total_tickets']}")
        print("="*60 + "\n")


async def main():
    """Main entry point."""
    csv_path = Path(__file__).parent.parent / "data" / "gold - gold.csv"
    
    if not csv_path.exists():
        print(f"ERROR: CSV file not found at {csv_path}")
        sys.exit(1)
    
    loader = RealDataLoader(str(csv_path))
    
    try:
        # Load CSV
        loader.load_csv()
        
        # Connect to databases
        await loader.connect()
        
        # Clear and rebuild
        await loader.clear_existing_data()
        await loader.build_graph()
        
        # Create Milvus collection and load embeddings
        # This requires OpenAI API key
        if loader.milvus and settings.openai_api_key:
            print("\nCreating Milvus collection with real data embeddings...")
            await loader.create_milvus_collection()
            await loader.load_embeddings(max_tickets=2000)  # Limit for cost
        
        # Print final stats
        await loader.print_statistics()
        
    finally:
        await loader.close()


if __name__ == "__main__":
    asyncio.run(main())

