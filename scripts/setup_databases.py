#!/usr/bin/env python3
"""
Database Setup Script

Initializes Neo4j and Milvus with the classification hierarchy and synthetic data.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nexusflow.config import settings
from nexusflow.db.neo4j_client import Neo4jClient
from nexusflow.db.milvus_client import MilvusClient
from nexusflow.services.embeddings import EmbeddingService


async def setup_neo4j():
    """Setup Neo4j with classification hierarchy."""
    print("\n🔷 Setting up Neo4j...")
    
    client = Neo4jClient()
    await client.connect()
    
    # Create schema
    print("  Creating schema...")
    await client.create_schema()
    
    # Load hierarchy
    hierarchy_file = Path(__file__).parent.parent / "data" / "classification_hierarchy.json"
    if hierarchy_file.exists():
        print("  Loading classification hierarchy...")
        await client.load_hierarchy_from_file(str(hierarchy_file))
        print("  ✓ Hierarchy loaded")
    else:
        print("  ⚠ Hierarchy file not found. Run generate_synthetic_data.py first.")
    
    # Get stats
    stats = await client.get_graph_statistics()
    print(f"  Graph stats: {stats}")
    
    await client.close()
    print("✓ Neo4j setup complete")


def setup_milvus():
    """Setup Milvus collection."""
    print("\n🔷 Setting up Milvus...")
    
    client = MilvusClient()
    client.connect()
    
    # Create collection
    print("  Creating collection...")
    client.create_collection(drop_existing=True)
    
    # Get stats
    stats = client.get_collection_stats()
    print(f"  Collection stats: {stats}")
    
    client.close()
    print("✓ Milvus setup complete")


async def load_synthetic_data():
    """Load synthetic ticket data into databases."""
    print("\n🔷 Loading synthetic data...")
    
    tickets_file = Path(__file__).parent.parent / "data" / "synthetic_tickets.json"
    if not tickets_file.exists():
        print("  ⚠ Synthetic tickets file not found. Run generate_synthetic_data.py first.")
        return
    
    with open(tickets_file) as f:
        tickets = json.load(f)
    
    print(f"  Found {len(tickets)} tickets")
    
    # Initialize services
    neo4j = Neo4jClient()
    await neo4j.connect()
    
    milvus = MilvusClient()
    milvus.connect()
    milvus.create_collection()
    
    embeddings = EmbeddingService()
    
    # Process tickets in batches
    batch_size = 50
    total = len(tickets)
    
    for i in range(0, total, batch_size):
        batch = tickets[i:i + batch_size]
        print(f"  Processing batch {i // batch_size + 1}/{(total + batch_size - 1) // batch_size}...")
        
        # Generate embeddings
        texts = [f"{t['title']}\n{t['description']}" for t in batch]
        try:
            batch_embeddings = await embeddings.embed_texts(texts)
        except Exception as e:
            print(f"    ⚠ Embedding generation failed: {e}")
            continue
        
        # Prepare data for Milvus
        milvus_data = []
        for j, ticket in enumerate(batch):
            milvus_data.append({
                "id": ticket["id"],
                "embedding": batch_embeddings[j],
                "title": ticket["title"],
                "description": ticket["description"],
                "level1_category": ticket["level1_category"],
                "level2_category": ticket["level2_category"],
                "level3_category": ticket["level3_category"],
                "was_correct": ticket.get("classification_was_correct", True),
                "confidence": 0.9,
            })
        
        # Insert into Milvus
        try:
            milvus.insert_tickets_batch(milvus_data)
        except Exception as e:
            print(f"    ⚠ Milvus insert failed: {e}")
        
        # Update Neo4j category counts
        for ticket in batch:
            try:
                await neo4j.add_ticket_to_graph(
                    ticket_id=ticket["id"],
                    level3_category=ticket["level3_category"],
                    confidence=0.9,
                )
            except Exception as e:
                pass  # Ignore individual failures
    
    # Load collection into memory
    milvus.load_collection()
    
    await neo4j.close()
    milvus.close()
    
    print(f"✓ Loaded {total} tickets into databases")


async def main():
    """Main setup function."""
    print("=" * 60)
    print("NexusFlow Database Setup")
    print("=" * 60)
    
    # Generate synthetic data first
    print("\n📊 Generating synthetic data...")
    from generate_synthetic_data import main as generate_data
    generate_data()
    
    # Setup databases
    await setup_neo4j()
    setup_milvus()
    
    # Load data
    await load_synthetic_data()
    
    print("\n" + "=" * 60)
    print("✅ Database setup complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

