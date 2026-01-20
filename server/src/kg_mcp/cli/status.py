#!/usr/bin/env python3
"""
Status and health check command for MCP-KG-Memory.

Provides a quick overview of system health:
- Docker status
- Neo4j container health
- Configuration summary
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError:
    print("Installing rich...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "-q"])
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

console = Console()


def check_docker_running() -> Tuple[bool, str]:
    """Check if Docker daemon is running."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, "Running"
        return False, "Not running"
    except FileNotFoundError:
        return False, "Not installed"
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)


def check_neo4j_container() -> Tuple[bool, str, Optional[str]]:
    """Check Neo4j container status."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=kg-memory-neo4j", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            status = result.stdout.strip()
            is_healthy = "healthy" in status.lower() or "Up" in status
            return is_healthy, status, None
        
        # Check if container exists but is stopped
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=kg-memory-neo4j", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.stdout.strip():
            return False, f"Stopped: {result.stdout.strip()}", "Run: docker compose up -d neo4j"
        
        return False, "Not created", "Run: docker compose up -d neo4j"
    except Exception as e:
        return False, str(e), None


def get_neo4j_ports() -> Tuple[Optional[str], Optional[str]]:
    """Get Neo4j port mappings."""
    try:
        result = subprocess.run(
            ["docker", "port", "kg-memory-neo4j"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            browser_port = "7474"
            bolt_port = "7687"
            for line in result.stdout.strip().split("\n"):
                if "7474" in line:
                    browser_port = line.split(":")[-1]
                elif "7687" in line:
                    bolt_port = line.split(":")[-1]
            return browser_port, bolt_port
    except Exception:
        pass
    return "7474", "7687"


def get_config() -> dict:
    """Load configuration from environment or config file."""
    config = {
        "neo4j_uri": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.environ.get("NEO4J_USER", "neo4j"),
        "neo4j_password": os.environ.get("NEO4J_PASSWORD", ""),
        "llm_model": os.environ.get("LLM_MODEL", "gemini/gemini-2.5-pro-preview-05-06"),
        "has_gemini_key": bool(os.environ.get("GEMINI_API_KEY")),
        "has_litellm_key": bool(os.environ.get("LITELLM_API_KEY")),
    }
    
    # Try to load from .env in common locations
    for env_path in [
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
        Path.home() / ".kg-mcp" / "config.json",
    ]:
        if env_path.exists():
            if env_path.suffix == ".json":
                try:
                    with open(env_path) as f:
                        config.update(json.load(f))
                except Exception:
                    pass
            else:
                # Parse .env file
                try:
                    with open(env_path) as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, value = line.split("=", 1)
                                key = key.strip().lower()
                                value = value.strip().strip('"').strip("'")
                                if key == "neo4j_uri":
                                    config["neo4j_uri"] = value
                                elif key == "neo4j_user":
                                    config["neo4j_user"] = value
                                elif key == "neo4j_password":
                                    config["neo4j_password"] = value
                                elif key == "llm_model":
                                    config["llm_model"] = value
                                elif key == "gemini_api_key" and value:
                                    config["has_gemini_key"] = True
                                elif key == "litellm_api_key" and value:
                                    config["has_litellm_key"] = True
                except Exception:
                    pass
    
    return config


def check_docker_autostart() -> Tuple[bool, str]:
    """Check if Docker Desktop is configured to start on login (macOS)."""
    if sys.platform != "darwin":
        return True, "N/A (non-macOS)"
    
    # Check Docker Desktop plist
    plist_path = Path.home() / "Library" / "LaunchAgents" / "com.docker.docker.plist"
    docker_app_settings = Path.home() / "Library" / "Group Containers" / "group.com.docker" / "settings.json"
    
    try:
        if docker_app_settings.exists():
            with open(docker_app_settings) as f:
                settings = json.load(f)
                if settings.get("openAtStartup", False):
                    return True, "Enabled"
    except Exception:
        pass
    
    return False, "Disabled (enable in Docker Desktop → Settings → General → Start Docker Desktop when you sign in)"


def print_status():
    """Print comprehensive status."""
    console.print()
    console.print(Panel("[bold]🧠 MCP-KG-Memory Status[/]", style="blue"))
    console.print()
    
    # Docker status
    docker_ok, docker_status = check_docker_running()
    docker_icon = "✅" if docker_ok else "❌"
    console.print(f"  {docker_icon} Docker: [{'green' if docker_ok else 'red'}]{docker_status}[/]")
    
    if not docker_ok:
        console.print()
        console.print("  [yellow]💡 Tip: Start Docker Desktop and try again[/]")
        console.print()
        return
    
    # Docker auto-start
    autostart_ok, autostart_status = check_docker_autostart()
    autostart_icon = "✅" if autostart_ok else "⚠️"
    console.print(f"  {autostart_icon} Docker Auto-Start: [{'green' if autostart_ok else 'yellow'}]{autostart_status}[/]")
    
    # Neo4j container
    neo4j_ok, neo4j_status, neo4j_fix = check_neo4j_container()
    neo4j_icon = "✅" if neo4j_ok else "❌"
    console.print(f"  {neo4j_icon} Neo4j Container: [{'green' if neo4j_ok else 'red'}]{neo4j_status}[/]")
    
    if neo4j_fix:
        console.print(f"     └─ [yellow]Fix: {neo4j_fix}[/]")
    
    # Neo4j endpoints
    if neo4j_ok:
        browser_port, bolt_port = get_neo4j_ports()
        console.print(f"     └─ Browser: [cyan]http://localhost:{browser_port}[/]")
        console.print(f"     └─ Bolt: [cyan]bolt://localhost:{bolt_port}[/]")
    
    # Configuration
    config = get_config()
    console.print()
    console.print("  [bold]Configuration:[/]")
    
    llm_ok = config["has_gemini_key"] or config["has_litellm_key"]
    llm_icon = "✅" if llm_ok else "❌"
    llm_provider = "Gemini" if config["has_gemini_key"] else ("LiteLLM" if config["has_litellm_key"] else "Not configured")
    console.print(f"  {llm_icon} LLM Provider: [{'green' if llm_ok else 'red'}]{llm_provider}[/]")
    console.print(f"     └─ Model: [dim]{config['llm_model']}[/]")
    
    if config["neo4j_password"]:
        pwd_display = config["neo4j_password"][:4] + "..." if len(config["neo4j_password"]) > 4 else "***"
    else:
        pwd_display = "[not set]"
    console.print(f"  ℹ️  Neo4j User: [dim]{config['neo4j_user']}[/] / Password: [dim]{pwd_display}[/]")
    
    # Overall status
    console.print()
    all_ok = docker_ok and neo4j_ok and llm_ok
    if all_ok:
        console.print(Panel("[bold green]✓ All systems operational![/]", style="green"))
    else:
        issues = []
        if not docker_ok:
            issues.append("Docker not running")
        if not neo4j_ok:
            issues.append("Neo4j not healthy")
        if not llm_ok:
            issues.append("LLM not configured")
        console.print(Panel(f"[bold yellow]⚠️ Issues: {', '.join(issues)}[/]", style="yellow"))
    
    console.print()


def doctor():
    """Run diagnostics and attempt to fix common issues."""
    console.print()
    console.print(Panel("[bold]🩺 MCP-KG-Memory Doctor[/]", style="blue"))
    console.print()
    
    issues_found = 0
    issues_fixed = 0
    
    # Check Docker
    docker_ok, docker_status = check_docker_running()
    if not docker_ok:
        issues_found += 1
        console.print("  ❌ Docker is not running")
        if sys.platform == "darwin":
            console.print("     Attempting to start Docker Desktop...")
            try:
                subprocess.run(["open", "-a", "Docker"], check=True)
                console.print("     [green]✓ Docker Desktop launched. Please wait ~30 seconds.[/]")
                issues_fixed += 1
            except Exception as e:
                console.print(f"     [red]Failed: {e}[/]")
    else:
        console.print("  ✅ Docker is running")
    
    if docker_ok:
        # Check Neo4j container
        neo4j_ok, neo4j_status, _ = check_neo4j_container()
        if not neo4j_ok:
            issues_found += 1
            console.print("  ❌ Neo4j container is not running")
            console.print("     Attempting to start Neo4j...")
            try:
                # Find project root
                for check_dir in [Path.cwd(), Path.cwd().parent]:
                    if (check_dir / "docker-compose.yml").exists():
                        result = subprocess.run(
                            ["docker", "compose", "up", "-d", "neo4j"],
                            cwd=check_dir,
                            capture_output=True,
                            text=True,
                        )
                        if result.returncode == 0:
                            console.print("     [green]✓ Neo4j container started[/]")
                            issues_fixed += 1
                        else:
                            console.print(f"     [red]Failed: {result.stderr}[/]")
                        break
                else:
                    console.print("     [yellow]Could not find docker-compose.yml[/]")
            except Exception as e:
                console.print(f"     [red]Failed: {e}[/]")
        else:
            console.print("  ✅ Neo4j container is healthy")
    
    # Check LLM configuration
    config = get_config()
    if not config["has_gemini_key"] and not config["has_litellm_key"]:
        issues_found += 1
        console.print("  ❌ LLM not configured")
        console.print("     [yellow]Run 'kg-mcp-setup' to configure LLM API key[/]")
    else:
        console.print("  ✅ LLM is configured")
    
    # Summary
    console.print()
    if issues_found == 0:
        console.print(Panel("[bold green]✓ No issues found![/]", style="green"))
    elif issues_fixed == issues_found:
        console.print(Panel(f"[bold green]✓ Fixed {issues_fixed}/{issues_found} issues![/]", style="green"))
    else:
        console.print(Panel(f"[bold yellow]⚠️ Fixed {issues_fixed}/{issues_found} issues. Some require manual intervention.[/]", style="yellow"))
    
    console.print()


def main():
    """Entry point for kg-mcp-status command."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP-KG-Memory status and diagnostics")
    parser.add_argument(
        "--doctor", "-d",
        action="store_true",
        help="Run diagnostics and attempt to fix common issues"
    )
    
    args = parser.parse_args()
    
    if args.doctor:
        doctor()
    else:
        print_status()


if __name__ == "__main__":
    main()
