#!/usr/bin/env python3
"""
Generate synthetic test tickets for testing classification pipeline.

Creates tickets with varying complexity to test:
- High confidence auto-resolution (clear, straightforward tickets)
- Low confidence HITL routing (ambiguous, complex tickets)
- Edge cases (mixed categories, unusual requests)
"""

import asyncio
import random
from datetime import datetime

# Test tickets designed to trigger different confidence levels
TEST_TICKETS = [
    # HIGH CONFIDENCE - Should auto-resolve (clear category matches)
    {
        "title": "Cannot login to my account - password reset needed",
        "description": "I forgot my password and need to reset it. When I try to login, it says invalid credentials. Please help me regain access to my account.",
        "expected_confidence": "high",
        "expected_category": "Account Access"
    },
    {
        "title": "Refund request for order #12345",
        "description": "I received my order but the item was damaged during shipping. I would like a full refund. The product has scratches and dents all over it.",
        "expected_confidence": "high",
        "expected_category": "Refunds"
    },
    {
        "title": "How do I change my shipping address?",
        "description": "I need to update my shipping address for future orders. I recently moved to a new location. Where can I find this setting in my account?",
        "expected_confidence": "high",
        "expected_category": "Account Management"
    },
    {
        "title": "Product not working - warranty claim",
        "description": "The laptop I purchased 3 months ago stopped working. The screen is completely black and it won't turn on. I believe this should be covered under warranty.",
        "expected_confidence": "high",
        "expected_category": "Warranty"
    },
    {
        "title": "Cancel my subscription",
        "description": "Please cancel my premium subscription immediately. I no longer need the service and do not want to be charged next month.",
        "expected_confidence": "high",
        "expected_category": "Subscription"
    },
    
    # MEDIUM CONFIDENCE - May or may not auto-resolve
    {
        "title": "Issue with my recent purchase",
        "description": "There's a problem with something I bought recently. Not sure if I need a refund, exchange, or technical support. The item isn't what I expected.",
        "expected_confidence": "medium",
        "expected_category": "ambiguous"
    },
    {
        "title": "Account and billing question",
        "description": "I have questions about my account and the charges on my credit card. Some charges look unfamiliar but I'm not sure if they're related to my subscription or a separate purchase.",
        "expected_confidence": "medium",
        "expected_category": "ambiguous"
    },
    {
        "title": "Need help ASAP",
        "description": "Something's wrong and I need immediate assistance. This is urgent! Please contact me as soon as possible.",
        "expected_confidence": "medium",
        "expected_category": "ambiguous"
    },
    
    # LOW CONFIDENCE - Should route to HITL (complex, ambiguous)
    {
        "title": "Multiple issues - please read carefully",
        "description": """I have several problems:
1. My password doesn't work sometimes
2. I was charged twice last month
3. The product I received was wrong color
4. My subscription shows as expired but I paid
5. Can't download the software I purchased
Please help with ALL of these issues.""",
        "expected_confidence": "low",
        "expected_category": "multiple"
    },
    {
        "title": "Complaint and legal inquiry",
        "description": "I am extremely dissatisfied with your service. I want to know your company's legal department contact and your refund policy. I may need to escalate this matter to consumer protection authorities.",
        "expected_confidence": "low",
        "expected_category": "escalation"
    },
    {
        "title": "Strange behavior on website",
        "description": "When I click the button it does something weird. Not sure how to describe it. Sometimes it works, sometimes it doesn't. It's been happening for a while.",
        "expected_confidence": "low",
        "expected_category": "vague"
    },
    {
        "title": "Partnership opportunity",
        "description": "Hello, I represent a company that would like to explore partnership opportunities with your organization. We believe there could be mutual benefits. Who should I speak with?",
        "expected_confidence": "low",
        "expected_category": "non-support"
    },
    {
        "title": "RE: FW: Previous conversation",
        "description": "As discussed previously, please see attached. Let me know your thoughts on the matter we talked about last week.",
        "expected_confidence": "low",
        "expected_category": "context-missing"
    },
    
    # EDGE CASES
    {
        "title": "Bad experience with your service",
        "description": "Not happy!!! Fix this NOW or I'm leaving a 1-star review everywhere!!! This is unacceptable customer service!",
        "expected_confidence": "low",
        "expected_category": "emotional"
    },
    {
        "title": "Technical error code: ERR_CONNECTION_REFUSED",
        "description": "Getting error ERR_CONNECTION_REFUSED when trying to access the API endpoint /api/v2/users. Stack trace: TypeError: Cannot read property 'data' of undefined at processRequest (app.js:142)",
        "expected_confidence": "medium",
        "expected_category": "technical"
    },
]


async def classify_ticket_via_api(ticket_data: dict) -> dict:
    """Classify a ticket directly through the API (creates and classifies in one call)."""
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        payload = {
            "title": ticket_data["title"],
            "description": ticket_data["description"],
            "priority": random.choice(["low", "medium", "high", "urgent"]),
            "source": "test_generator",
            "metadata": {
                "expected_confidence": ticket_data.get("expected_confidence", "unknown"),
                "expected_category": ticket_data.get("expected_category", "unknown"),
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        async with session.post(
            "http://localhost:8000/api/v1/classification/classify",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120)  # 2 minute timeout for LLM calls
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                print(f"Error: {response.status} - {text[:200]}")
                return None


async def main():
    print("=" * 70)
    print("  SYNTHETIC TICKET GENERATOR FOR TESTING CLASSIFICATION PIPELINE")
    print("=" * 70)
    print()
    print("This will create test tickets and classify them through the full pipeline:")
    print("  → Graph traversal (Neo4j)")
    print("  → Vector similarity (Milvus)")  
    print("  → LLM judgment (GPT-4o)")
    print("  → Ensemble confidence scoring")
    print("  → Auto-resolve or route to HITL")
    print()
    
    results = {
        "total": len(TEST_TICKETS),
        "classified": 0,
        "auto_resolved": 0,
        "sent_to_hitl": 0,
        "errors": 0,
        "by_expected": {"high": [], "medium": [], "low": []}
    }
    
    for i, ticket_data in enumerate(TEST_TICKETS):
        print(f"\n[{i+1}/{len(TEST_TICKETS)}] {ticket_data['title'][:55]}...")
        print(f"    Expected: {ticket_data['expected_confidence'].upper()} confidence")
        
        result = await classify_ticket_via_api(ticket_data)
        
        if result:
            results["classified"] += 1
            
            # Extract results
            confidence = result.get("confidence", {})
            # Use calibrated_score as the ensemble confidence
            ensemble_conf = confidence.get("calibrated_score", 0) or confidence.get("ensemble", 0)
            graph_conf = confidence.get("graph_confidence", 0)
            vector_conf = confidence.get("vector_confidence", 0)
            llm_conf = confidence.get("llm_confidence", 0)
            routing = result.get("routing", {})
            auto_resolved = routing.get("auto_resolved", False)
            classification = result.get("classification", {})
            level3 = classification.get("level3", "Unknown")
            
            # Track result
            expected = ticket_data.get("expected_confidence", "unknown")
            results["by_expected"][expected].append({
                "title": ticket_data["title"][:40],
                "confidence": ensemble_conf,
                "auto_resolved": auto_resolved
            })
            
            if auto_resolved:
                results["auto_resolved"] += 1
                status = "✓ AUTO-RESOLVED"
                color = "\033[92m"  # Green
            else:
                results["sent_to_hitl"] += 1
                status = "→ HITL QUEUE"
                color = "\033[93m"  # Yellow
            
            print(f"    {color}{status}\033[0m | Final: {ensemble_conf*100:.1f}% | Category: {level3}")
            print(f"      Components: Graph={graph_conf*100:.0f}% | Vector={vector_conf*100:.0f}% | LLM={llm_conf*100:.0f}%")
        else:
            results["errors"] += 1
            print(f"    \033[91m✗ FAILED\033[0m")
    
    print()
    print("=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Total tickets:      {results['total']}")
    print(f"  Successfully classified: {results['classified']}")
    print(f"  Auto-resolved:      {results['auto_resolved']} ({results['auto_resolved']/max(1,results['classified'])*100:.0f}%)")
    print(f"  Sent to HITL:       {results['sent_to_hitl']} ({results['sent_to_hitl']/max(1,results['classified'])*100:.0f}%)")
    print(f"  Errors:             {results['errors']}")
    print()
    
    print("  BY EXPECTED CONFIDENCE:")
    for exp_level in ["high", "medium", "low"]:
        tickets = results["by_expected"][exp_level]
        if tickets:
            auto = sum(1 for t in tickets if t["auto_resolved"])
            avg_conf = sum(t["confidence"] for t in tickets) / len(tickets)
            print(f"    {exp_level.upper():6} → Avg confidence: {avg_conf*100:.1f}% | Auto-resolved: {auto}/{len(tickets)}")
    
    print()
    if results['sent_to_hitl'] > 0:
        print("=" * 70)
        print(f"  🎯 {results['sent_to_hitl']} tickets sent to HITL queue for human review!")
        print(f"     Visit: http://localhost:3000/hitl")
        print("=" * 70)


if __name__ == "__main__":
    try:
        import aiohttp
    except ImportError:
        print("\nInstalling aiohttp...")
        import subprocess
        subprocess.run(["uv", "pip", "install", "aiohttp"], check=True)
        import aiohttp
    
    asyncio.run(main())

