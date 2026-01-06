"""
NexusFlow CLI

Command-line interface for NexusFlow operations.
"""

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

app = typer.Typer(
    name="nexusflow",
    help="NexusFlow - Intelligent Ticket Classification System",
    add_completion=False,
)

console = Console()


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to listen on"),
    reload: bool = typer.Option(False, help="Enable auto-reload"),
):
    """Start the NexusFlow API server."""
    import uvicorn

    console.print(
        Panel.fit(
            "[bold blue]NexusFlow[/bold blue] API Server",
            subtitle=f"http://{host}:{port}",
        )
    )

    uvicorn.run(
        "nexusflow.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command()
def mcp(
    host: str = typer.Option("0.0.0.0", help="Host to bind to"),
    port: int = typer.Option(8001, help="Port to listen on"),
):
    """Start the NexusFlow MCP server."""
    from nexusflow.mcp.server import run_mcp_server

    console.print(
        Panel.fit(
            "[bold purple]NexusFlow[/bold purple] MCP Server",
            subtitle=f"http://{host}:{port}",
        )
    )

    asyncio.run(run_mcp_server(host=host, port=port))


@app.command()
def classify(
    title: str = typer.Argument(..., help="Ticket title"),
    description: str = typer.Argument(..., help="Ticket description"),
    priority: str = typer.Option("medium", help="Priority level"),
):
    """Classify a single ticket from the command line."""
    from nexusflow.models.ticket import TicketCreate, TicketPriority
    from nexusflow.services.classification import ClassificationService

    async def run_classification():
        service = ClassificationService()

        try:
            priority_enum = TicketPriority(priority.lower())
        except ValueError:
            priority_enum = TicketPriority.MEDIUM

        ticket = TicketCreate(
            title=title,
            description=description,
            priority=priority_enum,
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Classifying ticket...", total=None)
            result = await service.classify_ticket(ticket)
            progress.update(task, completed=True)

        return result

    result = asyncio.run(run_classification())

    # Display results
    classification = result["classification"]
    confidence = result["confidence"]
    routing = result["routing"]

    console.print("\n[bold green]Classification Result[/bold green]")
    console.print(f"  Level 1: [cyan]{classification['level1']}[/cyan]")
    console.print(f"  Level 2: [cyan]{classification['level2']}[/cyan]")
    console.print(f"  Level 3: [cyan]{classification['level3']}[/cyan]")

    console.print("\n[bold yellow]Confidence Scores[/bold yellow]")
    console.print(f"  Graph:     {confidence['graph_confidence']:.2%}")
    console.print(f"  Vector:    {confidence['vector_confidence']:.2%}")
    console.print(f"  LLM:       {confidence['llm_confidence']:.2%}")
    console.print(f"  [bold]Final:     {confidence['calibrated_score']:.2%}[/bold]")

    if routing["auto_resolved"]:
        console.print("\n[bold green]✓ Auto-resolved[/bold green]")
    else:
        console.print(f"\n[bold orange]⚠ Requires review: {routing['hitl_reason']}[/bold orange]")


@app.command()
def setup(
    generate_data: bool = typer.Option(True, help="Generate synthetic data"),
    setup_neo4j: bool = typer.Option(True, help="Setup Neo4j"),
    setup_milvus: bool = typer.Option(True, help="Setup Milvus"),
):
    """Setup databases and load initial data."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

    from scripts.generate_synthetic_data import main as generate_main
    from scripts.setup_databases import setup_milvus as milvus_setup
    from scripts.setup_databases import setup_neo4j as neo4j_setup

    if generate_data:
        console.print("[bold]Generating synthetic data...[/bold]")
        generate_main()

    if setup_neo4j:
        console.print("\n[bold]Setting up Neo4j...[/bold]")
        asyncio.run(neo4j_setup())

    if setup_milvus:
        console.print("\n[bold]Setting up Milvus...[/bold]")
        milvus_setup()

    console.print("\n[bold green]✓ Setup complete![/bold green]")


@app.command()
def test():
    """Run API tests."""
    import subprocess

    subprocess.run(["python", "scripts/test_api.py"])


@app.command()
def stats():
    """Show system statistics."""
    from nexusflow.db.milvus_client import MilvusClient
    from nexusflow.db.neo4j_client import Neo4jClient

    async def get_stats():
        neo4j = Neo4jClient()
        await neo4j.connect()
        graph_stats = await neo4j.get_graph_statistics()
        await neo4j.close()

        milvus = MilvusClient()
        milvus.connect()
        vector_stats = milvus.get_collection_stats()
        milvus.close()

        return graph_stats, vector_stats

    graph_stats, vector_stats = asyncio.run(get_stats())

    table = Table(title="NexusFlow Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Level 1 Categories", str(graph_stats.get("level1_categories", 0)))
    table.add_row("Level 2 Categories", str(graph_stats.get("level2_categories", 0)))
    table.add_row("Level 3 Categories", str(graph_stats.get("level3_categories", 0)))
    table.add_row("Total Tickets (Graph)", str(graph_stats.get("total_tickets", 0)))
    table.add_row("Vector Embeddings", str(vector_stats.get("num_entities", 0)))

    console.print(table)


@app.command()
def version():
    """Show version information."""
    from nexusflow import __version__

    console.print(f"NexusFlow v{__version__}")


if __name__ == "__main__":
    app()
