#!/usr/bin/env python3
"""
API Test Script

Tests all NexusFlow API endpoints to ensure everything works correctly.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

# API Base URL
API_BASE = "http://localhost:8000"


def print_result(name: str, success: bool, details: str = ""):
    """Print test result."""
    icon = "✅" if success else "❌"
    print(f"  {icon} {name}")
    if details:
        print(f"     {details}")


async def test_tickets():
    """Test ticket CRUD endpoints."""
    print("\n🎫 Testing Ticket Endpoints")
    print("-" * 40)
    
    created_ticket_id = None
    
    async with httpx.AsyncClient() as client:
        # Create ticket
        try:
            response = await client.post(
                f"{API_BASE}/api/v1/tickets",
                json={
                    "title": "Test ticket for API testing",
                    "description": "This is a test ticket created by the API test script.",
                    "priority": "medium"
                }
            )
            if response.status_code == 200:
                data = response.json()
                created_ticket_id = data.get("ticket", {}).get("id")
                print_result("Create ticket", True, f"ID: {created_ticket_id}")
            else:
                print_result("Create ticket", False, response.text)
        except Exception as e:
            print_result("Create ticket", False, str(e))
        
        # List tickets
        try:
            response = await client.get(f"{API_BASE}/api/v1/tickets")
            success = response.status_code == 200
            total = response.json().get("total", 0) if success else 0
            print_result("List tickets", success, f"Total: {total}")
        except Exception as e:
            print_result("List tickets", False, str(e))
        
        # Get ticket
        if created_ticket_id:
            try:
                response = await client.get(f"{API_BASE}/api/v1/tickets/{created_ticket_id}")
                success = response.status_code == 200
                print_result("Get ticket", success)
            except Exception as e:
                print_result("Get ticket", False, str(e))
        
            # Update ticket
            try:
                response = await client.put(
                    f"{API_BASE}/api/v1/tickets/{created_ticket_id}",
                    json={"priority": "high"}
                )
                success = response.status_code == 200
                print_result("Update ticket", success)
            except Exception as e:
                print_result("Update ticket", False, str(e))
            
            # Delete ticket
            try:
                response = await client.delete(f"{API_BASE}/api/v1/tickets/{created_ticket_id}")
                success = response.status_code == 200
                print_result("Delete ticket", success)
            except Exception as e:
                print_result("Delete ticket", False, str(e))


async def test_health():
    """Test health endpoints."""
    print("\n📋 Testing Health Endpoints")
    print("-" * 40)
    
    async with httpx.AsyncClient() as client:
        # Health check
        try:
            response = await client.get(f"{API_BASE}/health")
            data = response.json()
            print_result(
                "Health check",
                response.status_code == 200,
                f"Status: {data.get('status')}, Version: {data.get('version')}"
            )
        except Exception as e:
            print_result("Health check", False, str(e))
        
        # Readiness check
        try:
            response = await client.get(f"{API_BASE}/health/ready")
            success = response.status_code == 200
            print_result("Readiness check", success)
        except Exception as e:
            print_result("Readiness check", False, str(e))


async def test_classification():
    """Test classification endpoints."""
    print("\n🎯 Testing Classification Endpoints")
    print("-" * 40)
    
    test_ticket = {
        "title": "Cannot reset password after account lockout",
        "description": "I've been trying to reset my password but the reset link keeps expiring before I can use it. This started happening after my account was locked due to too many failed login attempts.",
        "priority": "high"
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Single classification
        try:
            start = time.time()
            response = await client.post(
                f"{API_BASE}/api/v1/classification/classify",
                json=test_ticket
            )
            elapsed = (time.time() - start) * 1000
            
            if response.status_code == 200:
                data = response.json()
                classification = data.get("classification", {})
                confidence = data.get("confidence", {})
                print_result(
                    "Single classification",
                    True,
                    f"Category: {classification.get('level1')} > {classification.get('level2')} > {classification.get('level3')}"
                )
                print_result(
                    "  Confidence scores",
                    True,
                    f"Graph: {confidence.get('graph_confidence', 0):.2f}, "
                    f"Vector: {confidence.get('vector_confidence', 0):.2f}, "
                    f"LLM: {confidence.get('llm_confidence', 0):.2f}, "
                    f"Final: {confidence.get('calibrated_score', 0):.2f}"
                )
                print_result(
                    "  Processing time",
                    elapsed < 10000,
                    f"{elapsed:.0f}ms"
                )
            else:
                print_result("Single classification", False, response.text)
        except Exception as e:
            print_result("Single classification", False, str(e))
        
        # Get suggestions
        try:
            response = await client.post(
                f"{API_BASE}/api/v1/classification/suggest",
                json=test_ticket
            )
            success = response.status_code == 200
            count = response.json().get("count", 0) if success else 0
            print_result("Get suggestions", success, f"Got {count} suggestions")
        except Exception as e:
            print_result("Get suggestions", False, str(e))
        
        # Get hierarchy
        try:
            response = await client.get(f"{API_BASE}/api/v1/classification/hierarchy")
            success = response.status_code == 200
            stats = response.json().get("statistics", {}) if success else {}
            print_result(
                "Get hierarchy",
                success,
                f"Categories: L1={stats.get('level1_categories', 0)}, "
                f"L2={stats.get('level2_categories', 0)}, "
                f"L3={stats.get('level3_categories', 0)}"
            )
        except Exception as e:
            print_result("Get hierarchy", False, str(e))


async def test_batch():
    """Test batch processing endpoints."""
    print("\n📦 Testing Batch Endpoints")
    print("-" * 40)
    
    test_tickets = [
        {"title": "Payment not processing", "description": "Card keeps getting declined", "priority": "high"},
        {"title": "Need API documentation", "description": "Looking for REST API docs", "priority": "low"},
        {"title": "Account locked", "description": "Can't login to my account", "priority": "critical"},
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Submit batch
        batch_id = None
        try:
            response = await client.post(
                f"{API_BASE}/api/v1/batch/submit",
                json={"tickets": test_tickets}
            )
            if response.status_code == 200:
                data = response.json()
                batch_id = data.get("batch_id")
                print_result("Submit batch", True, f"Batch ID: {batch_id}")
            else:
                print_result("Submit batch", False, response.text)
        except Exception as e:
            print_result("Submit batch", False, str(e))
        
        # Check status
        if batch_id:
            try:
                response = await client.get(f"{API_BASE}/api/v1/batch/{batch_id}/status")
                success = response.status_code == 200
                status = response.json().get("status") if success else "unknown"
                print_result("Check batch status", success, f"Status: {status}")
            except Exception as e:
                print_result("Check batch status", False, str(e))
        
        # List batches
        try:
            response = await client.get(f"{API_BASE}/api/v1/batch")
            success = response.status_code == 200
            count = response.json().get("count", 0) if success else 0
            print_result("List batches", success, f"Found {count} batches")
        except Exception as e:
            print_result("List batches", False, str(e))


async def test_hitl():
    """Test HITL endpoints."""
    print("\n👥 Testing HITL Endpoints")
    print("-" * 40)
    
    async with httpx.AsyncClient() as client:
        # List tasks
        try:
            response = await client.get(f"{API_BASE}/api/v1/hitl/tasks")
            success = response.status_code == 200
            total = response.json().get("total", 0) if success else 0
            print_result("List HITL tasks", success, f"Total: {total}")
        except Exception as e:
            print_result("List HITL tasks", False, str(e))
        
        # Get stats
        try:
            response = await client.get(f"{API_BASE}/api/v1/hitl/stats")
            success = response.status_code == 200
            print_result("Get HITL stats", success)
        except Exception as e:
            print_result("Get HITL stats", False, str(e))


async def test_users():
    """Test user endpoints."""
    print("\n👤 Testing User Endpoints")
    print("-" * 40)
    
    async with httpx.AsyncClient() as client:
        # Login
        try:
            response = await client.post(
                f"{API_BASE}/api/v1/users/login",
                json={"email": "marawan.y@turing.com", "password": "admin123"}
            )
            success = response.status_code == 200
            if success:
                token = response.json().get("access_token", "")[:20] + "..."
                print_result("Login", True, f"Token: {token}")
            else:
                print_result("Login", False, response.text)
        except Exception as e:
            print_result("Login", False, str(e))
        
        # Get current user (with auth bypass)
        try:
            response = await client.get(f"{API_BASE}/api/v1/users/me")
            success = response.status_code == 200
            email = response.json().get("email") if success else "unknown"
            print_result("Get current user", success, f"Email: {email}")
        except Exception as e:
            print_result("Get current user", False, str(e))


async def test_analytics():
    """Test analytics endpoints."""
    print("\n📊 Testing Analytics Endpoints")
    print("-" * 40)
    
    async with httpx.AsyncClient() as client:
        # Dashboard stats
        try:
            response = await client.get(f"{API_BASE}/api/v1/analytics/dashboard")
            success = response.status_code == 200
            if success:
                data = response.json()
                print_result(
                    "Dashboard stats",
                    True,
                    f"Processed: {data.get('total_tickets_processed', 0)}, "
                    f"Categories: {data.get('graph_categories', 0)}"
                )
            else:
                print_result("Dashboard stats", False, response.text)
        except Exception as e:
            print_result("Dashboard stats", False, str(e))
        
        # Graph visualization
        try:
            response = await client.get(f"{API_BASE}/api/v1/analytics/graph/visualization")
            success = response.status_code == 200
            if success:
                data = response.json()
                print_result(
                    "Graph visualization",
                    True,
                    f"Nodes: {len(data.get('nodes', []))}, Edges: {len(data.get('edges', []))}"
                )
            else:
                print_result("Graph visualization", False, response.text)
        except Exception as e:
            print_result("Graph visualization", False, str(e))
        
        # Confidence metrics
        try:
            response = await client.get(f"{API_BASE}/api/v1/analytics/metrics/confidence")
            success = response.status_code == 200
            print_result("Confidence metrics", success)
        except Exception as e:
            print_result("Confidence metrics", False, str(e))


async def main():
    """Run all tests."""
    print("=" * 60)
    print("NexusFlow API Test Suite")
    print("=" * 60)
    print(f"\nAPI Base URL: {API_BASE}")
    
    await test_health()
    await test_tickets()
    await test_classification()
    await test_batch()
    await test_hitl()
    await test_users()
    await test_analytics()
    
    print("\n" + "=" * 60)
    print("Test suite complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

