import asyncio
import sys
import logging
from rich.console import Console
from rich.panel import Panel

# Ensure we can import from server
sys.path.append("server/src")

from kg_mcp.config import get_settings
from kg_mcp.llm.client import get_llm_client

console = Console()
logging.basicConfig(level=logging.ERROR)

async def run_verification():
    console.print(Panel("[bold]System Verification / Doctor Mode[/]", border_style="blue"))

    # 1. Config Loading
    console.print("[bold]1. Loading Configuration...[/]")
    try:
        settings = get_settings()
        console.print(f"[green]✓[/] Settings loaded.")
        console.print(f"   • Mode: [cyan]{settings.llm_mode}[/]")
        console.print(f"   • Primary: [cyan]{settings.llm_primary}[/]")
        console.print(f"   • Model: [cyan]{settings.llm_model}[/]")
        if settings.llm_mode in ["gemini_direct", "both"]:
             console.print(f"   • Gemini Key: {'[green]Set[/]' if settings.gemini_api_key else '[red]Missing[/]'}")
        if settings.llm_mode in ["litellm", "both"]:
             console.print(f"   • LiteLLM Key: {'[green]Set[/]' if settings.litellm_api_key else '[red]Missing[/]'}")
             console.print(f"   • LiteLLM Base: {settings.litellm_base_url}")
    except Exception as e:
        console.print(f"[red]✗ Config load failed:[/]\n{e}")
        return

    # 2. Client Initialization
    console.print("\n[bold]2. Initializing LLM Client...[/]")
    try:
        client = get_llm_client()
        console.print(f"[green]✓[/] Client initialized.")
        console.print(f"   • Active Provider: [cyan]{getattr(client, 'provider', 'unknown')}[/]")
        console.print(f"   • Active Model: [cyan]{client.model}[/]")
    except Exception as e:
        console.print(f"[red]✗ Client init failed:[/]\n{e}")
        return

    # 3. Neo4j Connection Test
    console.print("\n[bold]3. Testing Neo4j Connectivity...[/]")
    if settings.neo4j_configured != "0" and settings.neo4j_uri:
        try:
             from neo4j import GraphDatabase
             driver = GraphDatabase.driver(
                 settings.neo4j_uri, 
                 auth=(settings.neo4j_user, settings.neo4j_password)
             )
             driver.verify_connectivity()
             console.print(f"[green]✓[/] Neo4j Bolt Connection OK ({settings.neo4j_uri})")
             driver.close()
        except ImportError:
             console.print("[yellow]![/] Neo4j driver not installed (pip install neo4j). Skipping.[/]")
        except Exception as e:
             console.print(f"[red]✗ Neo4j Connection Failed:[/]\n{e}")
    else:
        console.print("[dim]Neo4j not configured or skipped.[/]")

    # 4. LLM Connectivity Test
    console.print("\n[bold]4. Testing LLM Connectivity...[/]")
    try:
        # Simple extraction test
        text = "My goal is to test the system."
        console.print(f"   Sending query: [italic]'{text}'[/]")
        
        result = await client.extract_entities(text)
        
        if result and result.confidence > 0:
            console.print(f"[green]✓[/] LLM Call Successful!")
            console.print(f"   • Confidence: {result.confidence}")
            console.print(f"   • Extracted Goals: {len(result.goals)}")
            if len(result.goals) > 0:
                 console.print(f"   • Goal Title: [italic]{result.goals[0].title}[/]")
        else:
            console.print("[yellow]![/] LLM returned empty or low confidence result.")
            
    except Exception as e:
        console.print(f"[red]✗ LLM Call Failed:[/]\n{e}")
        return
        
    console.print("\n[bold green]System is READY for deployment.[/]")

if __name__ == "__main__":
    try:
        asyncio.run(run_verification())
    except KeyboardInterrupt:
        pass
