#!/usr/bin/env python3
"""
Generate batch dataset from original gold CSV for batch upload demonstration.

Maps the original format to the batch API format:
- Inquiry Short Description -> title
- Inquiry_Details -> description  
- Product -> metadata.product
- BU -> metadata.bu
- Report_Category -> metadata.expected_category
"""

import csv
import json
import random
import sys
from pathlib import Path

# Original dataset path
GOLD_CSV = Path(__file__).parent.parent / "data" / "gold - gold.csv"
OUTPUT_JSON = Path(__file__).parent.parent / "data" / "batch_10k_sample.json"


def load_original_dataset(limit: int = None) -> list[dict]:
    """Load tickets from original CSV."""
    tickets = []
    
    with open(GOLD_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            
            # Map to batch format
            title = row.get('Inquiry Short Description', '').strip()
            description = row.get('Inquiry_Details', '').strip()
            
            if not title or not description:
                continue
            
            ticket = {
                "title": title[:200],  # Truncate very long titles
                "description": description[:2000],  # Truncate very long descriptions
                "priority": random.choice(["low", "medium", "high", "urgent"]),
                "source": "batch_upload",
                "metadata": {
                    "case_num": row.get('Case_Num', ''),
                    "product": row.get('Product', ''),
                    "bu": row.get('BU', ''),
                    "expected_category": row.get('Report_Category', ''),
                    "environment": row.get('Environment', ''),
                    "regulatory": row.get('Regulatory', ''),
                    "original_quality": row.get('ticket_quality', ''),
                }
            }
            tickets.append(ticket)
    
    return tickets


def create_batch_payload(tickets: list[dict], batch_size: int = 100) -> list[dict]:
    """Create batch payloads suitable for API submission."""
    batches = []
    
    for i in range(0, len(tickets), batch_size):
        batch = {
            "tickets": tickets[i:i + batch_size],
            "batch_id": f"demo_batch_{i // batch_size + 1:04d}"
        }
        batches.append(batch)
    
    return batches


def main():
    print("=" * 60)
    print("  BATCH DATASET GENERATOR")
    print("=" * 60)
    
    # Check if source file exists
    if not GOLD_CSV.exists():
        print(f"ERROR: Source file not found: {GOLD_CSV}")
        sys.exit(1)
    
    # Count total rows
    with open(GOLD_CSV, 'r', encoding='utf-8') as f:
        total_rows = sum(1 for _ in f) - 1  # Subtract header
    
    print(f"\nSource file: {GOLD_CSV}")
    print(f"Total rows in source: {total_rows:,}")
    
    # Load and convert tickets
    print("\nLoading and converting tickets...")
    target_count = min(10000, total_rows)
    
    # Load all and randomly sample if more than 10K
    all_tickets = load_original_dataset()
    print(f"Loaded {len(all_tickets):,} valid tickets")
    
    if len(all_tickets) > target_count:
        tickets = random.sample(all_tickets, target_count)
    else:
        tickets = all_tickets
    
    print(f"Selected {len(tickets):,} tickets for batch")
    
    # Create single batch payload for API
    batch_payload = {
        "tickets": tickets
    }
    
    # Save to JSON
    print(f"\nSaving to: {OUTPUT_JSON}")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(batch_payload, f, indent=2)
    
    # Also create a smaller sample for quick testing
    small_sample_path = OUTPUT_JSON.parent / "batch_100_sample.json"
    small_batch = {
        "tickets": random.sample(tickets, min(100, len(tickets)))
    }
    with open(small_sample_path, 'w', encoding='utf-8') as f:
        json.dump(small_batch, f, indent=2)
    
    print(f"Small sample (100): {small_sample_path}")
    
    # Print statistics
    print("\n" + "=" * 60)
    print("  STATISTICS")
    print("=" * 60)
    
    # Priority distribution
    priority_dist = {}
    for t in tickets:
        p = t["priority"]
        priority_dist[p] = priority_dist.get(p, 0) + 1
    
    print("\nPriority Distribution:")
    for p, count in sorted(priority_dist.items()):
        print(f"  {p}: {count:,} ({count/len(tickets)*100:.1f}%)")
    
    # Category distribution (from metadata)
    category_dist = {}
    for t in tickets:
        cat = t["metadata"].get("expected_category", "Unknown")
        category_dist[cat] = category_dist.get(cat, 0) + 1
    
    print(f"\nTop 10 Expected Categories:")
    for cat, count in sorted(category_dist.items(), key=lambda x: -x[1])[:10]:
        print(f"  {cat}: {count:,}")
    
    # Sample ticket
    print("\n" + "=" * 60)
    print("  SAMPLE TICKET")
    print("=" * 60)
    sample = tickets[0]
    print(f"\nTitle: {sample['title'][:80]}...")
    print(f"Description: {sample['description'][:200]}...")
    print(f"Priority: {sample['priority']}")
    print(f"Expected Category: {sample['metadata']['expected_category']}")
    
    print("\n" + "=" * 60)
    print("  USAGE")
    print("=" * 60)
    print(f"""
To upload via API:
  curl -X POST http://localhost:8000/api/v1/batch/submit \\
    -H "Content-Type: application/json" \\
    -d @{OUTPUT_JSON}

Or use the web interface:
  http://localhost:3000/batch
""")


if __name__ == "__main__":
    main()

