#!/usr/bin/env python3
"""
Interactive Setup Wizard for MCP-KG-Memory Server.

Guides developers through complete setup:
1. Neo4j configuration (local Docker or remote)
2. LLM API credentials (LiteLLM Gateway or direct Gemini)
3. Antigravity IDE integration
4. Schema application and verification
"""

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.markdown import Markdown
except ImportError:
    print("Installing rich for beautiful CLI output...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "-q"])
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    from rich.markdown import Markdown

console = Console()


class SetupWizard:
    """Interactive setup wizard for MCP-KG-Memory."""

    def __init__(self):
        self.config = {}
        self.project_root = self._find_project_root()

    def _find_project_root(self) -> Path:
        """Find the project root directory or create one for pipx installations."""
        current = Path.cwd()
        
        # Check if we're in the server directory
        if (current / "pyproject.toml").exists() and (current / "src" / "kg_mcp").exists():
            return current.parent
        
        # Check if we're in the project root
        if (current / "server" / "pyproject.toml").exists():
            return current
        
        # Check parent directories
        for parent in current.parents:
            if (parent / "server" / "pyproject.toml").exists():
                return parent
            if (parent / "docker-compose.yml").exists():
                return parent
        
        # Not in a project directory - likely installed via pipx
        # Use ~/.kg-mcp as the project root
        kg_mcp_home = Path.home() / ".kg-mcp"
        kg_mcp_home.mkdir(exist_ok=True)
        
        # Download docker-compose.yml if not present
        dc_path = kg_mcp_home / "docker-compose.yml"
        if not dc_path.exists():
            self._download_docker_compose(dc_path)
        
        return kg_mcp_home

    def _download_docker_compose(self, target_path: Path):
        """Download docker-compose.yml from GitHub."""
        import urllib.request
        
        console.print("  [dim]Downloading docker-compose.yml from GitHub...[/]")
        
        url = "https://raw.githubusercontent.com/Hexecu/mcp-neuralmemory/main/docker-compose.yml"
        
        try:
            urllib.request.urlretrieve(url, target_path)
            console.print(f"  [green]✓[/] Downloaded to {target_path}")
        except Exception as e:
            console.print(f"  [red]✗[/] Failed to download: {e}")
            console.print("  [yellow]You can manually download from:[/]")
            console.print(f"    [cyan]{url}[/]")
            console.print(f"  [yellow]And save to: {target_path}[/]")

    def run(self):
        """Run the complete setup wizard."""
        self._print_welcome()
        
        try:
            # Step 0: Verify Docker
            self._check_docker()
            
            # Step 1: Neo4j Configuration
            self._setup_neo4j()
            
            # Step 2: LLM Configuration
            self._setup_llm()
            
            # Step 3: Security Configuration
            self._setup_security()
            
            # Step 4: Generate .env file
            self._generate_env_file()
            
            # Step 5: Start Neo4j if needed
            if self.config.get("start_neo4j_docker"):
                self._start_neo4j()
            
            # Step 6: Apply Schema
            if self.config.get("apply_schema"):
                self._apply_schema()
            
            # Step 7: Configure Antigravity
            if Confirm.ask("\n[cyan]Configure Antigravity IDE integration?[/]", default=True):
                self._configure_antigravity()
            
            # Step 8: Summary
            self._print_summary()
            
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Setup cancelled.[/]")
            sys.exit(1)

    def _print_welcome(self):
        """Print welcome banner."""
        welcome = """
# 🧠 MCP-KG-Memory Setup Wizard

Welcome! This wizard will help you set up the Memory/Knowledge Graph MCP Server.

**What you'll need:**
- Docker (for local Neo4j) OR remote Neo4j credentials
- LiteLLM Gateway credentials OR Gemini API key

Let's get started!
        """
        console.print(Panel(Markdown(welcome), title="Setup Wizard", border_style="green"))
        console.print()

    def _check_docker(self):
        """Verify Docker is installed and running."""
        console.print(Panel("[bold]Step 0: Docker Verification[/]", style="blue"))
        
        # Check if Docker is installed
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            docker_installed = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            docker_installed = False
        
        if not docker_installed:
            console.print("  [red]✗[/] Docker is not installed")
            console.print()
            console.print("  [bold]Please install Docker Desktop:[/]")
            if sys.platform == "darwin":
                console.print("    [cyan]https://docs.docker.com/desktop/install/mac-install/[/]")
            elif sys.platform == "win32":
                console.print("    [cyan]https://docs.docker.com/desktop/install/windows-install/[/]")
            else:
                console.print("    [cyan]https://docs.docker.com/desktop/install/linux-install/[/]")
            console.print()
            if not Confirm.ask("Continue anyway (use remote Neo4j)?", default=False):
                sys.exit(1)
            return
        
        console.print("  [green]✓[/] Docker is installed")
        
        # Check if Docker daemon is running
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            docker_running = result.returncode == 0
        except subprocess.TimeoutExpired:
            docker_running = False
        
        if not docker_running:
            console.print("  [yellow]![/] Docker daemon is not running")
            
            if sys.platform == "darwin":
                if Confirm.ask("Start Docker Desktop now?", default=True):
                    console.print("  Starting Docker Desktop...")
                    subprocess.run(["open", "-a", "Docker"], check=False)
                    console.print("  [dim]Please wait for Docker to start (~30 seconds)...[/]")
                    
                    import time
                    for i in range(30):
                        time.sleep(1)
                        try:
                            result = subprocess.run(
                                ["docker", "info"],
                                capture_output=True,
                                timeout=2,
                            )
                            if result.returncode == 0:
                                console.print("  [green]✓[/] Docker is now running")
                                break
                        except Exception:
                            pass
                    else:
                        console.print("  [yellow]![/] Docker is still starting, continuing anyway...")
            else:
                console.print("  [yellow]Please start Docker and run this wizard again[/]")
                if not Confirm.ask("Continue anyway?", default=False):
                    sys.exit(1)
        else:
            console.print("  [green]✓[/] Docker daemon is running")
        
        console.print()

    def _setup_neo4j(self):
        """Configure Neo4j database."""
        console.print(Panel("[bold]Step 1: Neo4j Database Configuration[/]", style="blue"))
        
        neo4j_mode = Prompt.ask(
            "How would you like to run Neo4j?",
            choices=["docker", "remote", "existing"],
            default="docker"
        )
        
        if neo4j_mode == "docker":
            self.config["neo4j_uri"] = "bolt://localhost:7687"
            self.config["neo4j_user"] = "neo4j"
            
            password = Prompt.ask(
                "Neo4j password (leave empty for auto-generate)",
                password=True,
                default=""
            )
            if not password:
                password = secrets.token_urlsafe(16)
                console.print(f"  [green]✓[/] Generated password: [yellow]{password}[/]")
            
            self.config["neo4j_password"] = password
            self.config["start_neo4j_docker"] = Confirm.ask(
                "Start Neo4j Docker container now?",
                default=True
            )
            
        elif neo4j_mode == "remote":
            self.config["neo4j_uri"] = Prompt.ask(
                "Neo4j URI",
                default="bolt://your-neo4j-host:7687"
            )
            self.config["neo4j_user"] = Prompt.ask("Username", default="neo4j")
            self.config["neo4j_password"] = Prompt.ask("Password", password=True)
            self.config["start_neo4j_docker"] = False
            
        else:  # existing
            self.config["neo4j_uri"] = Prompt.ask(
                "Neo4j URI",
                default="bolt://localhost:7687"
            )
            self.config["neo4j_user"] = Prompt.ask("Username", default="neo4j")
            self.config["neo4j_password"] = Prompt.ask("Password", password=True)
            self.config["start_neo4j_docker"] = False
        
        self.config["apply_schema"] = Confirm.ask(
            "Apply Neo4j schema (constraints/indexes)?",
            default=True
        )
        
        console.print()

    def _setup_llm(self):
        """Configure LLM API."""
        console.print(Panel("[bold]Step 2: LLM API Configuration[/]", style="blue"))
        
        llm_mode = Prompt.ask(
            "LLM provider",
            choices=["litellm_gateway", "gemini_direct"],
            default="litellm_gateway"
        )
        
        if llm_mode == "litellm_gateway":
            self.config["litellm_base_url"] = Prompt.ask(
                "LiteLLM Gateway URL",
                default="https://your-litellm-gateway.io/"
            )
            self.config["litellm_api_key"] = Prompt.ask(
                "LiteLLM API Key",
                password=True
            )
            self.config["llm_model"] = Prompt.ask(
                "Model name",
                default="gemini-2.5-flash-preview-09-2025"
            )
            self.config["gemini_api_key"] = ""
        else:
            self.config["gemini_api_key"] = Prompt.ask(
                "Gemini API Key (from https://aistudio.google.com)",
                password=True
            )
            self.config["llm_model"] = Prompt.ask(
                "Model name",
                default="gemini/gemini-2.5-pro-preview-05-06"
            )
            self.config["litellm_base_url"] = ""
            self.config["litellm_api_key"] = ""
        
        console.print()

    def _setup_security(self):
        """Configure security settings."""
        console.print(Panel("[bold]Step 3: Security Configuration[/]", style="blue"))
        
        token = Prompt.ask(
            "MCP authentication token (leave empty for auto-generate)",
            password=True,
            default=""
        )
        if not token:
            token = f"kg-mcp-{secrets.token_urlsafe(24)}"
            console.print(f"  [green]✓[/] Generated token: [yellow]{token}[/]")
        
        self.config["kg_mcp_token"] = token
        self.config["allowed_origins"] = "localhost,127.0.0.1"
        
        console.print()

    def _generate_env_file(self):
        """Generate .env file."""
        console.print(Panel("[bold]Step 4: Generating Configuration[/]", style="blue"))
        
        env_path = self.project_root / ".env"
        
        env_content = f"""# MCP-KG-Memory Configuration
# Generated by kg-mcp-setup wizard

# Neo4j Database
NEO4J_URI={self.config['neo4j_uri']}
NEO4J_USER={self.config['neo4j_user']}
NEO4J_PASSWORD={self.config['neo4j_password']}

# LLM Configuration
LITELLM_BASE_URL={self.config.get('litellm_base_url', '')}
LITELLM_API_KEY={self.config.get('litellm_api_key', '')}
GEMINI_API_KEY={self.config.get('gemini_api_key', '')}
LLM_MODEL={self.config['llm_model']}

# MCP Server
MCP_HOST=127.0.0.1
MCP_PORT=8000
LOG_LEVEL=INFO

# Security
KG_MCP_TOKEN={self.config['kg_mcp_token']}
KG_ALLOWED_ORIGINS={self.config['allowed_origins']}
"""
        
        env_path.write_text(env_content)
        console.print(f"  [green]✓[/] Created: {env_path}")
        
        # Also update docker-compose if needed
        if self.config.get("start_neo4j_docker"):
            self._update_docker_compose()
        
        console.print()

    def _update_docker_compose(self):
        """Update docker-compose.yml with correct password."""
        dc_path = self.project_root / "docker-compose.yml"
        if dc_path.exists():
            content = dc_path.read_text()
            # Update the password in docker-compose if present
            if "NEO4J_AUTH" in content:
                import re
                new_auth = f"NEO4J_AUTH=neo4j/{self.config['neo4j_password']}"
                content = re.sub(
                    r"NEO4J_AUTH=neo4j/[^\s\"']*",
                    new_auth,
                    content
                )
                dc_path.write_text(content)
                console.print(f"  [green]✓[/] Updated: {dc_path}")

    def _start_neo4j(self):
        """Start Neo4j Docker container."""
        console.print(Panel("[bold]Step 5: Starting Neo4j[/]", style="blue"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Starting Neo4j container...", total=None)
            
            try:
                # First, set the password in environment
                env = os.environ.copy()
                env["NEO4J_AUTH"] = f"neo4j/{self.config['neo4j_password']}"
                
                result = subprocess.run(
                    ["docker", "compose", "up", "-d", "neo4j"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    env=env,
                )
                
                if result.returncode == 0:
                    console.print("  [green]✓[/] Neo4j container started")
                    console.print("  [dim]Waiting for Neo4j to be ready (30s)...[/]")
                    
                    # Wait for Neo4j to be healthy
                    import time
                    time.sleep(30)
                else:
                    console.print(f"  [red]✗[/] Failed to start: {result.stderr}")
                    
            except FileNotFoundError:
                console.print("  [red]✗[/] Docker not found. Please install Docker first.")
        
        console.print()

    def _apply_schema(self):
        """Apply Neo4j schema."""
        console.print(Panel("[bold]Step 6: Applying Neo4j Schema[/]", style="blue"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Applying schema...", total=None)
            
            try:
                # Load environment
                env = os.environ.copy()
                env.update({
                    "NEO4J_URI": self.config["neo4j_uri"],
                    "NEO4J_USER": self.config["neo4j_user"],
                    "NEO4J_PASSWORD": self.config["neo4j_password"],
                })
                
                result = subprocess.run(
                    [sys.executable, "-m", "kg_mcp.kg.apply_schema"],
                    cwd=self.project_root / "server",
                    capture_output=True,
                    text=True,
                    env=env,
                )
                
                if result.returncode == 0:
                    console.print("  [green]✓[/] Schema applied successfully")
                else:
                    console.print(f"  [yellow]![/] Schema application had issues: {result.stderr[:200]}")
                    
            except Exception as e:
                console.print(f"  [red]✗[/] Failed: {e}")
        
        console.print()

    def _configure_antigravity(self):
        """Configure Antigravity IDE integration."""
        console.print(Panel("[bold]Step 7: Antigravity IDE Configuration[/]", style="blue"))
        
        # Find Antigravity config
        antigravity_config_path = Path.home() / ".gemini" / "antigravity" / "mcp_config.json"
        
        if not antigravity_config_path.parent.exists():
            console.print("  [yellow]![/] Antigravity config directory not found")
            console.print(f"    Expected: {antigravity_config_path.parent}")
            if not Confirm.ask("Create it?", default=True):
                return
            antigravity_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing config
        existing_config = {}
        if antigravity_config_path.exists():
            try:
                existing_config = json.loads(antigravity_config_path.read_text())
            except json.JSONDecodeError:
                pass
        
        # Build kg-memory config
        server_venv = self.project_root / "server" / ".venv" / "bin" / "python"
        if not server_venv.exists():
            server_venv = Path(sys.executable)
        
        kg_memory_config = {
            "command": str(server_venv),
            "args": ["-m", "kg_mcp", "--transport", "stdio"],
            "env": {
                "NEO4J_URI": self.config["neo4j_uri"],
                "NEO4J_USER": self.config["neo4j_user"],
                "NEO4J_PASSWORD": self.config["neo4j_password"],
                "KG_MCP_TOKEN": self.config["kg_mcp_token"],
                "LLM_MODEL": self.config["llm_model"],
                "LOG_LEVEL": "INFO",
            }
        }
        
        # Add LLM config
        if self.config.get("litellm_base_url"):
            kg_memory_config["env"]["LITELLM_BASE_URL"] = self.config["litellm_base_url"]
            kg_memory_config["env"]["LITELLM_API_KEY"] = self.config["litellm_api_key"]
        elif self.config.get("gemini_api_key"):
            kg_memory_config["env"]["GEMINI_API_KEY"] = self.config["gemini_api_key"]
        
        # Merge with existing config
        if "mcpServers" not in existing_config:
            existing_config["mcpServers"] = {}
        
        existing_config["mcpServers"]["kg-memory"] = kg_memory_config
        
        # Write config
        antigravity_config_path.write_text(json.dumps(existing_config, indent=4))
        console.print(f"  [green]✓[/] Updated: {antigravity_config_path}")
        
        console.print()
        console.print("  [bold]Next steps in Antigravity:[/]")
        console.print("  1. Open Agent sidebar → ... → MCP Servers")
        console.print("  2. Click 'Manage MCP Servers' → 'Refresh'")
        console.print("  3. You should see 'kg-memory' with 5 tools")
        console.print()

    def _print_summary(self):
        """Print setup summary."""
        console.print()
        console.print(Panel("[bold green]✓ Setup Complete![/]", style="green"))
        
        table = Table(title="Configuration Summary")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Neo4j URI", self.config["neo4j_uri"])
        table.add_row("Neo4j User", self.config["neo4j_user"])
        table.add_row("LLM Model", self.config["llm_model"])
        table.add_row("Auth Token", f"{self.config['kg_mcp_token'][:20]}...")
        table.add_row(".env File", str(self.project_root / ".env"))
        
        console.print(table)
        
        # Neo4j Browser info
        if self.config.get("start_neo4j_docker") or "localhost" in self.config.get("neo4j_uri", ""):
            console.print()
            console.print(Panel(
                "[bold]Neo4j Browser[/]\n\n"
                f"URL: [cyan]http://localhost:7474[/]\n"
                f"Username: [green]{self.config['neo4j_user']}[/]\n"
                f"Password: [green]{self.config['neo4j_password']}[/]\n\n"
                "[dim]Use this to visualize your knowledge graph![/]",
                title="📊 Graph Visualization",
                style="green"
            ))
        
        console.print()
        console.print("[bold]Quick Start Commands:[/]")
        console.print()
        console.print("  # Check system status")
        console.print("  [cyan]kg-mcp-status[/]")
        console.print()
        console.print("  # Fix common issues")
        console.print("  [cyan]kg-mcp-status --doctor[/]")
        console.print()
        console.print("  # Start the MCP server (HTTP mode)")
        console.print(f"  [cyan]cd {self.project_root}/server && kg-mcp --transport http[/]")
        console.print()
        
        # Docker auto-start tip
        if sys.platform == "darwin":  # macOS
            console.print()
            console.print("[bold yellow]💡 Tip: Enable Docker auto-start[/]")
            console.print("  Docker Desktop → Settings → General → 'Start Docker Desktop when you sign in'")
            console.print("  This ensures Neo4j is always available after reboot.")
        
        console.print()


def main():
    """Entry point for kg-mcp-setup command."""
    wizard = SetupWizard()
    wizard.run()


if __name__ == "__main__":
    main()
