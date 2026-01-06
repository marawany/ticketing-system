#!/usr/bin/env python3
"""
Turing NexusFlow - HITL and Self-Learning Demonstration
========================================================
This script demonstrates:
1. Classification with confidence threshold routing
2. Automatic HITL task creation for low-confidence tickets
3. Human feedback submission
4. Self-learning system updating graph weights

Run: python scripts/demo_hitl.py
"""

import asyncio
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

API_URL = "http://localhost:8000/api/v1"

async def make_request(method: str, endpoint: str, data: dict = None, token: str = None):
    """Make HTTP request to API."""
    import aiohttp
    
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    url = f"{API_URL}{endpoint}"
    
    async with aiohttp.ClientSession() as session:
        if method == "GET":
            async with session.get(url, headers=headers, params=data) as resp:
                return await resp.json()
        elif method == "POST":
            async with session.post(url, headers=headers, json=data) as resp:
                return await resp.json()


async def main():
    console.print(Panel.fit(
        "[bold cyan]Turing NexusFlow[/bold cyan]\n"
        "[dim]HITL & Self-Learning Demonstration[/dim]",
        border_style="cyan"
    ))
    
    # Step 1: Login
    console.print("\n[bold cyan]━━━ Step 1: Authentication ━━━[/bold cyan]")
    
    login_data = await make_request("POST", "/users/login", {
        "email": "marawan.y@turing.com",
        "password": "admin123"
    })
    
    if "access_token" not in login_data:
        console.print("[red]Failed to login. Make sure the API is running.[/red]")
        return
    
    token = login_data["access_token"]
    console.print("[green]✓[/green] Logged in as marawan.y@turing.com")
    
    # Step 2: Show current HITL thresholds
    console.print("\n[bold cyan]━━━ Step 2: Configuration Thresholds ━━━[/bold cyan]")
    
    table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    table.add_column("Threshold", style="dim")
    table.add_column("Value", style="bold")
    table.add_column("Behavior", style="dim")
    
    table.add_row(
        "Auto-Resolve",
        "≥ 0.70",
        "Ticket resolved automatically"
    )
    table.add_row(
        "HITL Review",
        "0.50 - 0.69",
        "Routed to human for review"
    )
    table.add_row(
        "Escalation",
        "< 0.50",
        "Urgent escalation required"
    )
    console.print(table)
    
    # Step 3: Submit tickets with different confidence levels
    console.print("\n[bold cyan]━━━ Step 3: Classifying Tickets ━━━[/bold cyan]")
    
    test_tickets = [
        {
            "title": "Cannot reset password",
            "description": "I click the reset password link but get an error 500. Need urgent help!",
            "expected_confidence": "high",
            "expected_routing": "auto"
        },
        {
            "title": "App crashes sometimes when I open it",
            "description": "The app is crashing intermittently. Not sure if it's related to the latest update or my phone settings. Also my subscription might be expired?",
            "expected_confidence": "medium",
            "expected_routing": "hitl"
        },
        {
            "title": "qwerasdf",
            "description": "dfghjkl things stuff problem help please",
            "expected_confidence": "low",
            "expected_routing": "escalate"
        }
    ]
    
    classification_results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        for ticket in test_tickets:
            task = progress.add_task(f"Classifying: {ticket['title'][:30]}...", total=None)
            
            result = await make_request("POST", "/classification/classify", {
                "title": ticket["title"],
                "description": ticket["description"],
                "priority": "medium"
            }, token=token)
            
            classification_results.append({
                "ticket": ticket,
                "result": result
            })
            
            progress.remove_task(task)
            
            await asyncio.sleep(0.5)
    
    # Display results
    console.print("\n[bold]Classification Results:[/bold]")
    
    results_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    results_table.add_column("Ticket", style="dim", width=25)
    results_table.add_column("Classification", style="bold")
    results_table.add_column("Confidence", justify="center")
    results_table.add_column("Routing", style="bold")
    
    for item in classification_results:
        ticket = item["ticket"]
        result = item["result"]
        
        if "classification" in result:
            cls = result["classification"]
            conf = result.get("confidence", {})
            conf_score = conf.get("calibrated_score", 0) if isinstance(conf, dict) else conf
            
            # Determine confidence color
            if conf_score >= 0.7:
                conf_style = "[green]"
                routing = "[green]AUTO-RESOLVED[/green]"
            elif conf_score >= 0.5:
                conf_style = "[yellow]"
                routing = "[yellow]HITL QUEUE[/yellow]"
            else:
                conf_style = "[red]"
                routing = "[red]ESCALATION[/red]"
            
            results_table.add_row(
                ticket["title"][:25],
                f"{cls.get('level1', 'N/A')} → {cls.get('level2', 'N/A')}",
                f"{conf_style}{conf_score:.2f}[/{conf_style[1:]}",
                routing
            )
        else:
            results_table.add_row(
                ticket["title"][:25],
                "[red]Error[/red]",
                "-",
                "-"
            )
    
    console.print(results_table)
    
    # Step 4: Check HITL Queue
    console.print("\n[bold cyan]━━━ Step 4: HITL Queue Status ━━━[/bold cyan]")
    
    hitl_tasks = await make_request("GET", "/hitl/tasks", {"status": "pending"}, token=token)
    
    if hitl_tasks.get("total", 0) > 0:
        console.print(f"[yellow]✓[/yellow] {hitl_tasks['total']} task(s) in HITL queue")
        
        queue_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        queue_table.add_column("Task ID", style="dim")
        queue_table.add_column("Ticket", style="bold")
        queue_table.add_column("AI Classification")
        queue_table.add_column("Confidence")
        queue_table.add_column("Reason")
        
        for task in hitl_tasks.get("tasks", [])[:5]:
            queue_table.add_row(
                task["id"][:8] + "...",
                task.get("ticket_title", "N/A")[:20],
                task.get("ai_level1", "N/A"),
                f"[yellow]{task.get('ai_confidence', 0):.2f}[/yellow]",
                task.get("routing_reason", "Low confidence")[:20]
            )
        
        console.print(queue_table)
        
        # Step 5: Demonstrate Human Feedback (Self-Learning)
        console.print("\n[bold cyan]━━━ Step 5: Submit Human Correction (Self-Learning) ━━━[/bold cyan]")
        
        # Get first pending task
        task_to_review = hitl_tasks["tasks"][0]
        console.print(f"\n[dim]Reviewing task: {task_to_review['id'][:8]}...[/dim]")
        console.print(f"[dim]AI suggested: {task_to_review['ai_level1']} → {task_to_review['ai_level2']} → {task_to_review['ai_level3']}[/dim]")
        
        # Submit a correction - simulate human correcting the AI classification
        correction_data = {
            "task_id": task_to_review["id"],
            "corrected_level1": "Technical Support",
            "corrected_level2": "Application Issues",  # Corrected from Authentication
            "corrected_level3": "App Crashes",         # Corrected category
            "is_correct": False,  # AI was NOT correct
            "correction_notes": "This is about app crashes, not authentication",
            "review_time_seconds": 35,
            "confidence_feedback": "AI misclassified - should improve training"
        }
        
        console.print("\n[bold]Submitting human correction...[/bold]")
        correction_result = await make_request("POST", "/hitl/corrections", correction_data, token=token)
        
        if correction_result.get("id"):
            console.print("[green]✓[/green] Correction submitted successfully!")
            console.print(f"[dim]  Correction ID: {correction_result['id'][:8]}...[/dim]")
            console.print(f"[dim]  AI was correct: {correction_result.get('is_correct', False)}[/dim]")
            
            if not correction_result.get("is_correct", True):
                console.print("\n[bold magenta]Self-Learning Triggered:[/bold magenta]")
                console.print("  • Neo4j graph weights updated")
                console.print("  • Category accuracy scores adjusted")
                console.print("  • Edge weights modified for correct path")
        else:
            console.print(f"[yellow]Note: {correction_result.get('detail', 'Correction already exists')}[/yellow]")
    
    else:
        console.print("[green]✓[/green] No tasks in HITL queue (all auto-resolved)")
    
    # Step 6: Show System Learning Metrics
    console.print("\n[bold cyan]━━━ Step 6: System Learning Metrics ━━━[/bold cyan]")
    
    stats = await make_request("GET", "/hitl/stats", token=token)
    
    metrics_table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
    metrics_table.add_column("Metric", style="dim")
    metrics_table.add_column("Value", style="bold")
    
    metrics_table.add_row("Total Reviews", str(stats.get("total_completed", 0)))
    metrics_table.add_row("AI Accuracy", f"{stats.get('accuracy_rate', 0) * 100:.1f}%")
    metrics_table.add_row("Avg Review Time", f"{stats.get('avg_review_time_seconds', 0):.1f}s")
    metrics_table.add_row("Pending Tasks", str(stats.get("total_pending", 0)))
    
    console.print(metrics_table)
    
    # Step 7: Show Graph Evolution (Learning)
    console.print("\n[bold cyan]━━━ Step 7: Graph Evolution (Self-Learning) ━━━[/bold cyan]")
    
    graph_data = await make_request("GET", "/analytics/graph-visualization", token=token)
    
    if graph_data.get("nodes"):
        console.print(f"[green]✓[/green] Knowledge Graph Status:")
        console.print(f"  • Nodes: {len(graph_data.get('nodes', []))}")
        console.print(f"  • Edges: {len(graph_data.get('edges', []))}")
        console.print(f"  • Categories with weighted edges (learned from feedback)")
        
        # Show some edge weights if available
        console.print("\n[bold]Sample Edge Weights (adjusted by human feedback):[/bold]")
        for edge in graph_data.get("edges", [])[:3]:
            weight = edge.get("weight", 1.0)
            weight_style = "[green]" if weight > 1.0 else "[yellow]" if weight == 1.0 else "[red]"
            console.print(f"  {edge.get('source', 'N/A')} → {edge.get('target', 'N/A')}: {weight_style}{weight:.2f}[/{weight_style[1:]}")
    
    # Summary
    console.print("\n" + "━" * 60)
    console.print(Panel.fit(
        "[bold green]✓ HITL & Self-Learning Demo Complete![/bold green]\n\n"
        "The system demonstrates:\n"
        "• [cyan]Confidence-based routing[/cyan] (auto/HITL/escalation)\n"
        "• [cyan]Human review queue[/cyan] with task management\n"
        "• [cyan]Self-learning[/cyan] from human corrections\n"
        "• [cyan]Graph weight updates[/cyan] for improved accuracy",
        border_style="green"
    ))


if __name__ == "__main__":
    asyncio.run(main())

