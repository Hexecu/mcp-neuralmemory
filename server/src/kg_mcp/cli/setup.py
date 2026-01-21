#!/usr/bin/env python3
"""
MCP-KG-Memory Setup Wizard — GEMINI ONLY (Direct + LiteLLM), numeric menus

What it does:
- Guides setup with numeric choices (no strings to type for menus)
- Supports Gemini Direct (AI Studio / Gemini API) and Gemini via LiteLLM Gateway/Proxy
- Can configure either one, or both (and pick a primary)
- Generates a .env file (safe + backward compatible: LLM_MODEL still present)
- Optional: Neo4j local via Docker Compose or remote credentials
- Optional: apply Neo4j schema (if module exists)
- Optional: configure Antigravity MCP config (~/.gemini/antigravity/mcp_config.json)
- Optional: connectivity tests

Run:
  python3 kg_mcp_setup.py
"""

from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# -------------------------
# Dependency bootstrap
# -------------------------
def ensure(import_name: str, pip_name: Optional[str] = None) -> None:
    try:
        __import__(import_name)
    except ImportError:
        pkg = pip_name or import_name
        print(f"Installing dependency: {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])


ensure("rich")
ensure("requests")

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn

import requests

console = Console()


# -------------------------
# Constants (curated)
# -------------------------
# Main Gemini text models for KG/RAG workloads (from official Gemini API model list)
GEMINI_DIRECT_MODELS = [
    "gemini-2.5-flash",                    # best price/perf default
    "gemini-2.5-pro",                      # heavier reasoning
    "gemini-2.5-flash-lite",               # fastest/cost-efficient
    "gemini-2.5-flash-preview-09-2025",    # preview
    "gemini-2.5-flash-lite-preview-09-2025",
    # Specialized (you can still pick them if needed)
    "gemini-2.5-flash-image",
    "gemini-2.5-flash-native-audio-preview-12-2025",
]

# If you want to allow legacy / soon-to-retire models, keep them separated and warn.
GEMINI_LEGACY_OR_RISKY = [
    "gemini-2.0-flash",        # example: retirement warnings exist in some Google services
    "gemini-2.0-flash-lite",
]

# For LiteLLM, Gemini models must be sent as gemini/<model>
def litellm_wrap(model: str) -> str:
    if model.startswith("gemini/"):
        return model
    return f"gemini/{model}"


# -------------------------
# Small helpers
# -------------------------
def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        return url
    if not re.match(r"^https?://", url):
        url = "https://" + url
    url = url.rstrip("/") + "/"
    return url


def mask(s: str, keep: int = 4) -> str:
    if not s:
        return ""
    if len(s) <= keep:
        return "*" * len(s)
    return s[:keep] + "*" * (len(s) - keep)


def choose_numeric(title: str, options: List[str], default_index: int = 1) -> int:
    if default_index < 1 or default_index > len(options):
        default_index = 1

    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("#", style="bold yellow", width=4)
    table.add_column("Opzione", style="green")

    for i, opt in enumerate(options, start=1):
        suffix = "  [dim](default)[/]" if i == default_index else ""
        table.add_row(str(i), opt + suffix)

    console.print(table)

    while True:
        raw = Prompt.ask("Seleziona un numero", default=str(default_index)).strip()
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(options):
                return idx
        console.print("[red]Valore non valido. Inserisci un numero presente in lista.[/]")


def prompt_required(label: str, default: Optional[str] = None) -> str:
    while True:
        v = Prompt.ask(label, default=default or "").strip()
        if v:
            return v
        console.print("[red]Campo obbligatorio.[/]")


def prompt_secret_required(label: str, allow_empty: bool = False) -> str:
    while True:
        v = Prompt.ask(label, password=True, default="").strip()
        if v or allow_empty:
            return v
        console.print("[red]Campo obbligatorio.[/]")


def backup_file(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = path.with_suffix(path.suffix + f".bak-{ts}")
    shutil.copy2(path, bak)
    return bak


def safe_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_cmd(cmd: List[str], cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def docker_available() -> Tuple[bool, bool]:
    """Returns (installed, daemon_running)."""
    try:
        r = run_cmd(["docker", "--version"], timeout=5)
        installed = (r.returncode == 0)
    except Exception:
        installed = False

    if not installed:
        return False, False

    try:
        r = run_cmd(["docker", "info"], timeout=10)
        running = (r.returncode == 0)
    except Exception:
        running = False

    return True, running


def http_get(url: str, headers: Dict[str, str], timeout: int = 20) -> Tuple[bool, Any, str]:
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if 200 <= r.status_code < 300:
            try:
                return True, r.json(), ""
            except Exception:
                return True, r.text, ""
        return False, None, f"HTTP {r.status_code}: {r.text[:250]}"
    except Exception as e:
        return False, None, str(e)


def http_post(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: int = 30) -> Tuple[bool, Any, str]:
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if 200 <= r.status_code < 300:
            try:
                return True, r.json(), ""
            except Exception:
                return True, r.text, ""
        return False, None, f"HTTP {r.status_code}: {r.text[:250]}"
    except Exception as e:
        return False, None, str(e)


def find_project_root() -> Path:
    """
    Heuristics:
    - If we see server/pyproject.toml -> current is root
    - If current is server/ with pyproject.toml -> parent is root
    - Else walk parents; else fallback ~/.kg-mcp
    """
    cur = Path.cwd()

    if (cur / "server" / "pyproject.toml").exists():
        return cur
    if (cur / "pyproject.toml").exists() and cur.name == "server":
        return cur.parent

    for p in cur.parents:
        if (p / "server" / "pyproject.toml").exists():
            return p
        if (p / "docker-compose.yml").exists() and (p / "server").exists():
            return p

    home = Path.home() / ".kg-mcp"
    home.mkdir(parents=True, exist_ok=True)
    return home


# -------------------------
# Wizard
# -------------------------
class SetupWizard:
    def __init__(self) -> None:
        self.project_root = find_project_root()
        self.env_path = self.project_root / ".env"
        self.config: Dict[str, str] = {}

    def run(self) -> None:
        self._welcome()
        self._step_llm()
        self._step_neo4j()
        self._step_security()
        self._write_env()
        self._optional_start_neo4j()
        self._optional_apply_schema()
        self._optional_antigravity()
        self._summary()

    # -------------------------
    # Step 0: Welcome
    # -------------------------
    def _welcome(self) -> None:
        msg = f"""
# 🧠 MCP-KG-Memory Setup Wizard — Gemini only (Direct + LiteLLM)

Questo wizard crea una configurazione facile da usare.

**Supporta:**
- ✅ Gemini Direct (AI Studio key)
- ✅ Gemini via LiteLLM Gateway/Proxy (model prefix automatico)

**Output:**
- `.env` in: `{self.env_path}`

Andiamo.
        """.strip()
        console.print(Panel(Markdown(msg), border_style="green"))
        console.print()

    # -------------------------
    # Step 1: LLM
    # -------------------------
    def _step_llm(self) -> None:
        console.print(Panel("[bold]Step 1: LLM (Gemini)[/]", border_style="blue"))

        mode_opts = [
            "Solo Gemini Direct (AI Studio)",
            "Solo LiteLLM Gateway/Proxy (Gemini routed)",
            "Configura ENTRAMBI (e scegli primario)",
        ]
        mode = choose_numeric("Che modalità vuoi configurare?", mode_opts, default_index=1)

        if mode == 1:
            self._setup_gemini_direct()
            self.config["LLM_MODE"] = "gemini_direct"
            self.config["LLM_PROVIDER"] = "gemini"
            self.config["LLM_MODEL"] = self.config["GEMINI_MODEL"]
        elif mode == 2:
            self._setup_litellm_gemini()
            self.config["LLM_MODE"] = "litellm"
            self.config["LLM_PROVIDER"] = "litellm"
            self.config["LLM_MODEL"] = self.config["LITELLM_MODEL"]
        else:
            # both
            self._setup_gemini_direct()
            self._setup_litellm_gemini()

            primary_opts = [
                "Primario: Gemini Direct",
                "Primario: LiteLLM",
            ]
            primary = choose_numeric("Quale vuoi usare come default primario?", primary_opts, default_index=2)
            if primary == 1:
                self.config["LLM_MODE"] = "both"
                self.config["LLM_PRIMARY"] = "gemini_direct"
                self.config["LLM_PROVIDER"] = "gemini"
                self.config["LLM_MODEL"] = self.config["GEMINI_MODEL"]
            else:
                self.config["LLM_MODE"] = "both"
                self.config["LLM_PRIMARY"] = "litellm"
                self.config["LLM_PROVIDER"] = "litellm"
                self.config["LLM_MODEL"] = self.config["LITELLM_MODEL"]

        # Optional role-based models (useful for KG workloads)
        if Confirm.ask("Vuoi configurare modelli diversi per RUOLO (default/fast/reason)?", default=False):
            self._setup_role_models()

        console.print()

    def _setup_role_models(self) -> None:
        # Pick from direct list (text oriented) and keep consistent with chosen backend.
        # If primary is litellm, we store litellm-wrapped names; else direct names.
        primary = self.config.get("LLM_PROVIDER", "litellm")
        use_litellm_names = (primary == "litellm")

        def pick(title: str, default_model: str) -> str:
            base = GEMINI_DIRECT_MODELS[:3] + ["(legacy/risky) " + m for m in GEMINI_LEGACY_OR_RISKY] + ["Custom..."]
            idx = choose_numeric(title, base, default_index=1)
            choice = base[idx - 1]
            if choice == "Custom...":
                m = prompt_required("Inserisci model id (es: gemini-2.5-flash)")
            else:
                if choice.startswith("(legacy/risky) "):
                    m = choice.replace("(legacy/risky) ", "")
                    console.print("[yellow]![/] Nota: questo modello potrebbe avere retirement/deprecation in alcuni servizi. Usalo solo se necessario.")
                else:
                    m = choice

            if use_litellm_names:
                return litellm_wrap(m)
            return m

        # Default recommendation: flash; fast: flash-lite; reason: pro
        default_m = "gemini-2.5-flash"
        fast_m = "gemini-2.5-flash-lite"
        reason_m = "gemini-2.5-pro"

        self.config["KG_MODEL_DEFAULT"] = pick("Scegli KG_MODEL_DEFAULT", default_m)
        self.config["KG_MODEL_FAST"] = pick("Scegli KG_MODEL_FAST (operazioni veloci/high throughput)", fast_m)
        self.config["KG_MODEL_REASON"] = pick("Scegli KG_MODEL_REASON (reasoning/diagnostica)", reason_m)

    def _setup_gemini_direct(self) -> None:
        console.print(Panel("[bold]Gemini Direct[/]", border_style="cyan"))

        api_key = prompt_secret_required("GEMINI_API_KEY (da AI Studio)", allow_empty=False)
        self.config["GEMINI_API_KEY"] = api_key
        self.config["GEMINI_BASE_URL"] = "https://generativelanguage.googleapis.com/"

        model_opts = [
            "Scegli da lista consigliata (2.5 Flash/Pro/Flash-Lite)",
            "Mostrami la lista LIVE dei modelli disponibili (richiede key)",
            "Inserisci model id manualmente",
        ]
        pick_mode = choose_numeric("Come vuoi scegliere il modello?", model_opts, default_index=1)

        if pick_mode == 1:
            self.config["GEMINI_MODEL"] = self._pick_from_curated_direct()
        elif pick_mode == 2:
            live = self._gemini_list_models(api_key)
            if live:
                self.config["GEMINI_MODEL"] = self._pick_from_list("Scegli un modello (LIVE)", live, default="gemini-2.5-flash")
            else:
                console.print("[yellow]![/] Non sono riuscito a ottenere la lista LIVE. Uso lista consigliata.")
                self.config["GEMINI_MODEL"] = self._pick_from_curated_direct()
        else:
            self.config["GEMINI_MODEL"] = prompt_required("Model id (es: gemini-2.5-flash)")

        # Optional connectivity test
        if Confirm.ask("Vuoi testare ora Gemini Direct (generateContent)?", default=True):
            self._test_gemini_direct(api_key, self.config["GEMINI_MODEL"])

    def _pick_from_curated_direct(self) -> str:
        options = (
            ["gemini-2.5-flash  (default consigliato)"]
            + ["gemini-2.5-pro"]
            + ["gemini-2.5-flash-lite"]
            + ["Altri (preview/specializzati)..."]
            + ["Legacy/risky (2.0)..."]
            + ["Custom..."]
        )
        idx = choose_numeric("Seleziona categoria modello", options, default_index=1)

        if idx == 1:
            return "gemini-2.5-flash"
        if idx == 2:
            return "gemini-2.5-pro"
        if idx == 3:
            return "gemini-2.5-flash-lite"
        if idx == 4:
            return self._pick_from_list("Scegli (preview/specializzati)", GEMINI_DIRECT_MODELS[3:], default=GEMINI_DIRECT_MODELS[3])
        if idx == 5:
            console.print("[yellow]![/] Warning: alcuni servizi indicano retirement per 2.0 Flash/Flash-Lite entro il 2026. Usa 2.5 Flash-Lite come sostituto se puoi.")
            return self._pick_from_list("Scegli (legacy/risky)", GEMINI_LEGACY_OR_RISKY, default=GEMINI_LEGACY_OR_RISKY[0])
        return prompt_required("Model id custom (es: gemini-2.5-flash)")

    def _gemini_list_models(self, api_key: str) -> List[str]:
        # Gemini REST: GET v1beta/models?key=...
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        ok, data, err = http_get(url, headers={"Content-Type": "application/json"})
        if not ok:
            console.print(f"[yellow]![/] GET models fallito: {err}")
            return []
        try:
            models = data.get("models", [])
            names: List[str] = []
            for m in models:
                name = m.get("name", "")  # "models/gemini-2.5-flash"
                if name.startswith("models/"):
                    name = name[len("models/") :]
                if name:
                    names.append(name)
            # De-dup + stable ordering
            names = sorted(set(names))
            # prefer gemini-* first
            names = sorted(names, key=lambda s: (0 if s.startswith("gemini-") else 1, s))
            return names
        except Exception:
            console.print("[yellow]![/] Risposta ricevuta ma non parsabile come lista modelli.")
            return []

    def _test_gemini_direct(self, api_key: str, model: str) -> None:
        # POST generateContent
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": "ping (rispondi solo con 'pong')"}]}]}
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            p.add_task(description="Test Gemini Direct...", total=None)
            ok, data, err = http_post(url, headers={"Content-Type": "application/json"}, payload=payload, timeout=30)

        if ok:
            console.print("[green]✓[/] Gemini Direct OK.")
            try:
                txt = data["candidates"][0]["content"]["parts"][0]["text"]
                console.print(f"  Reply: {txt!r}")
            except Exception:
                console.print("  (OK ma risposta inattesa)")
        else:
            console.print(f"[yellow]![/] Test fallito: {err}")

    def _setup_litellm_gemini(self) -> None:
        console.print(Panel("[bold]LiteLLM Gateway/Proxy (Gemini)[/]", border_style="cyan"))

        base_url = prompt_required("LITELLM_BASE_URL (es: https://litellm.mycompany.com/ oppure http://localhost:4000/)")
        base_url = normalize_url(base_url)
        api_key = prompt_secret_required("LITELLM_API_KEY", allow_empty=False)

        self.config["LITELLM_BASE_URL"] = base_url
        self.config["LITELLM_API_KEY"] = api_key

        # Model selection
        model_opts = [
            "Scegli da lista consigliata (Gemini 2.5) [prefix automatico gemini/...]",
            "Prova a leggere la lista modelli dal Gateway (GET /v1/models) [se supportato]",
            "Inserisci model id manualmente",
        ]
        pick_mode = choose_numeric("Come vuoi scegliere il modello (LiteLLM)?", model_opts, default_index=1)

        if pick_mode == 1:
            m = self._pick_from_curated_direct()
            self.config["LITELLM_MODEL"] = litellm_wrap(m)
        elif pick_mode == 2:
            live = self._litellm_list_models(base_url, api_key)
            if live:
                picked = self._pick_from_list("Scegli un modello (Gateway)", live, default=self._best_default_from_gateway(live))
                self.config["LITELLM_MODEL"] = picked
                if not picked.startswith("gemini/"):
                    console.print("[yellow]![/] Nota: il gateway ha restituito un id senza prefisso 'gemini/'. Lo userò così com'è.")
            else:
                console.print("[yellow]![/] Non sono riuscito a ottenere la lista dal gateway. Uso lista consigliata.")
                m = self._pick_from_curated_direct()
                self.config["LITELLM_MODEL"] = litellm_wrap(m)
        else:
            raw = prompt_required("Model id (LiteLLM). Esempio: gemini/gemini-2.5-flash")
            # auto-fix if user pasted direct model
            self.config["LITELLM_MODEL"] = litellm_wrap(raw) if raw.startswith("gemini-") else raw

        # Optional connectivity test
        if Confirm.ask("Vuoi testare ora LiteLLM (POST /v1/chat/completions)?", default=True):
            self._test_litellm(base_url, api_key, self.config["LITELLM_MODEL"])

    def _litellm_list_models(self, base_url: str, api_key: str) -> List[str]:
        # common: /v1/models (OpenAI compatible)
        url = base_url.rstrip("/") + "/v1/models"
        ok, data, err = http_get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=20)
        if not ok:
            console.print(f"[yellow]![/] GET /v1/models fallito: {err}")
            return []
        try:
            items = data.get("data", [])
            ids = [it.get("id", "") for it in items if isinstance(it, dict)]
            ids = [x for x in ids if x]
            ids = sorted(set(ids))
            return ids
        except Exception:
            console.print("[yellow]![/] Risposta /v1/models ricevuta ma non parsabile.")
            return []

    def _best_default_from_gateway(self, ids: List[str]) -> str:
        # prefer gemini/gemini-2.5-flash if present
        preferred = [
            "gemini/gemini-2.5-flash",
            "gemini/gemini-2.5-flash-lite",
            "gemini/gemini-2.5-pro",
        ]
        for p in preferred:
            if p in ids:
                return p
        return ids[0] if ids else "gemini/gemini-2.5-flash"

    def _test_litellm(self, base_url: str, api_key: str, model: str) -> None:
        url = base_url.rstrip("/") + "/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "ping (rispondi solo con 'pong')"}],
            "max_tokens": 16,
        }
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            p.add_task(description="Test LiteLLM...", total=None)
            ok, data, err = http_post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                payload=payload,
                timeout=30,
            )

        if ok:
            console.print("[green]✓[/] LiteLLM OK.")
            try:
                txt = data["choices"][0]["message"]["content"]
                console.print(f"  Reply: {txt!r}")
            except Exception:
                console.print("  (OK ma risposta inattesa)")
        else:
            console.print(f"[yellow]![/] Test fallito: {err}")

    def _pick_from_list(self, title: str, items: List[str], default: str) -> str:
        # build numeric menu for up to N entries, else provide pagination-ish
        if not items:
            return default

        # Put default first if exists
        items_sorted = items[:]
        if default in items_sorted:
            items_sorted.remove(default)
            items_sorted.insert(0, default)

        # If huge list, show first 40 + custom
        max_show = 40
        shown = items_sorted[:max_show]
        options = shown + ["Custom..."]
        idx = choose_numeric(title, options, default_index=1)
        if idx == len(options):
            return prompt_required("Model id custom")
        return options[idx - 1]

    # -------------------------
    # Step 2: Neo4j
    # -------------------------
    def _step_neo4j(self) -> None:
        console.print(Panel("[bold]Step 2: Neo4j[/]", border_style="blue"))

        opts = [
            "Docker locale (compose auto se manca)",
            "Neo4j remoto (inserisco URI/user/pass)",
            "Skip Neo4j (lo configuro dopo)",
        ]
        c = choose_numeric("Come vuoi configurare Neo4j?", opts, default_index=1)

        if c == 3:
            self.config["NEO4J_CONFIGURED"] = "0"
            console.print("[yellow]Neo4j skipped.[/]\n")
            return

        self.config["NEO4J_CONFIGURED"] = "1"

        if c == 1:
            self.config["NEO4J_URI"] = "bolt://localhost:7687"
            self.config["NEO4J_USER"] = "neo4j"
            pw = Prompt.ask("Password Neo4j (invio = genera)", password=True, default="").strip()
            if not pw:
                pw = secrets.token_urlsafe(18)
                console.print(f"[green]✓[/] Password Neo4j generata: [yellow]{pw}[/]")
            self.config["NEO4J_PASSWORD"] = pw

            installed, running = docker_available()
            self.config["NEO4J_DOCKER_ENABLED"] = "1" if installed else "0"
            self.config["NEO4J_DOCKER_AUTOSTART"] = "1" if (installed and running and Confirm.ask("Avvio Neo4j ora?", default=True)) else "0"
        else:
            self.config["NEO4J_URI"] = prompt_required("NEO4J_URI (bolt://host:7687)", default="bolt://your-neo4j-host:7687")
            self.config["NEO4J_USER"] = Prompt.ask("NEO4J_USER", default="neo4j").strip() or "neo4j"
            self.config["NEO4J_PASSWORD"] = prompt_secret_required("NEO4J_PASSWORD", allow_empty=False)
            self.config["NEO4J_DOCKER_ENABLED"] = "0"
            self.config["NEO4J_DOCKER_AUTOSTART"] = "0"

        # Always apply schema (best practice)
        self.config["NEO4J_APPLY_SCHEMA"] = "1"
        console.print("[dim]Schema (constraints/indexes) will be applied automatically.[/]")
        console.print()

    # -------------------------
    # Step 3: Security
    # -------------------------
    def _step_security(self) -> None:
        console.print(Panel("[bold]Step 3: Security[/]", border_style="blue"))

        token = Prompt.ask("MCP auth token (invio = genera)", password=True, default="").strip()
        if not token:
            token = f"kg-mcp-{secrets.token_urlsafe(24)}"
            console.print("[green]✓[/] Token generato.")
        self.config["KG_MCP_TOKEN"] = token

        # safe defaults
        self.config["MCP_HOST"] = "127.0.0.1"
        self.config["MCP_PORT"] = "8000"
        self.config["LOG_LEVEL"] = "INFO"
        self.config["KG_ALLOWED_ORIGINS"] = "localhost,127.0.0.1"
        console.print()

    # -------------------------
    # Write .env
    # -------------------------
    def _write_env(self) -> None:
        console.print(Panel("[bold]Step 4: Genero .env[/]", border_style="blue"))

        if self.env_path.exists():
            bak = backup_file(self.env_path)
            console.print(f"[yellow]![/] Esiste già .env → backup creato: {bak}")

        # Stable ordering (grouped)
        groups: List[Tuple[str, List[str]]] = [
            ("# --- MCP ---", ["MCP_HOST", "MCP_PORT", "LOG_LEVEL", "KG_MCP_TOKEN", "KG_ALLOWED_ORIGINS"]),
            ("# --- LLM (primary) ---", ["LLM_MODE", "LLM_PRIMARY", "LLM_PROVIDER", "LLM_MODEL"]),
            ("# --- Gemini Direct ---", ["GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_BASE_URL"]),
            ("# --- LiteLLM (Gemini) ---", ["LITELLM_BASE_URL", "LITELLM_API_KEY", "LITELLM_MODEL"]),
            ("# --- KG Role Models (optional) ---", ["KG_MODEL_DEFAULT", "KG_MODEL_FAST", "KG_MODEL_REASON"]),
            ("# --- Neo4j ---", ["NEO4J_CONFIGURED", "NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "NEO4J_DOCKER_ENABLED", "NEO4J_DOCKER_AUTOSTART", "NEO4J_APPLY_SCHEMA"]),
        ]

        lines: List[str] = ["# Generated by MCP-KG-Memory setup wizard", ""]
        for header, keys in groups:
            present = [k for k in keys if k in self.config and self.config[k] != ""]
            if not present:
                continue
            lines.append(header)
            for k in keys:
                if k in self.config and self.config[k] != "":
                    lines.append(f"{k}={self.config[k]}")
            lines.append("")

        safe_write_text(self.env_path, "\n".join(lines).rstrip() + "\n")
        console.print(f"[green]✓[/] Scritto: {self.env_path}")
        console.print()

    # -------------------------
    # Optional: start Neo4j via Docker
    # -------------------------
    def _optional_start_neo4j(self) -> None:
        if self.config.get("NEO4J_DOCKER_AUTOSTART") != "1":
            return

        console.print(Panel("[bold]Step 5: Avvio Neo4j (Docker)[/]", border_style="blue"))

        installed, running = docker_available()
        if not installed:
            console.print("[red]✗ Docker non installato.[/]")
            return
        if not running:
            console.print("[red]✗ Docker daemon non in esecuzione. Avvia Docker Desktop e rilancia.[/]")
            return

        # ALWAYS check for existing volumes first (regardless of port status)
        # This prevents password mismatch when user re-runs setup
        existing_volumes = self._check_neo4j_volumes()
        if existing_volumes:
            console.print("[yellow]![/] Trovati volumi Neo4j esistenti da setup precedente.")
            console.print(f"[dim]Volumi: {', '.join(existing_volumes)}[/]")
            console.print("[dim]Una nuova password è stata generata - i volumi vecchi vanno rimossi.[/]")
            if Confirm.ask("Rimuovo i volumi esistenti? (i dati verranno persi)", default=True):
                # First stop any running containers
                for c in self._find_neo4j_containers():
                    run_cmd(["docker", "stop", c], timeout=30)
                    run_cmd(["docker", "rm", "-v", c], timeout=10)
                # Then remove volumes
                for vol in existing_volumes:
                    run_cmd(["docker", "volume", "rm", "-f", vol], timeout=10)
                console.print("[green]✓[/] Volumi e container rimossi.")
                time.sleep(1)
            else:
                console.print("[yellow]![/] Mantengo i volumi esistenti.")
                console.print("[dim]Nota: se la password nel .env è diversa da quella nel volume, Neo4j non partirà.[/]")

        # Check for port conflicts and offer to cleanup
        if self._check_port_conflict(7687) or self._check_port_conflict(7474):
            console.print("[yellow]![/] Le porte Neo4j (7474/7687) sono già in uso.")
            # Try to find and stop conflicting containers
            conflicting = self._find_neo4j_containers()
            if conflicting:
                console.print(f"[dim]Container esistenti: {', '.join(conflicting)}[/]")
                console.print("[dim]Nota: verranno rimossi anche i volumi per evitare conflitti password.[/]")
                if Confirm.ask("Fermo e rimuovo i container esistenti (e i volumi)?", default=True):
                    # Use docker compose down -v if compose file exists (most reliable)
                    compose_path = self.project_root / "docker-compose.yml"
                    if compose_path.exists():
                        run_cmd(["docker", "compose", "down", "-v"], cwd=self.project_root, timeout=60)
                    # Also stop/remove any containers by name
                    for c in conflicting:
                        run_cmd(["docker", "stop", c], timeout=30)
                        run_cmd(["docker", "rm", "-v", c], timeout=10)
                    # Force remove any lingering volumes by name pattern
                    for vol in ["kg-mcp_neo4j_data", "kg-mcp_neo4j_logs", 
                                "mcp-kg-memory_neo4j_data", "mcp-kg-memory_neo4j_logs"]:
                        run_cmd(["docker", "volume", "rm", "-f", vol], timeout=10)
                    console.print("[green]✓[/] Container e volumi rimossi.")
                    time.sleep(2)
                else:
                    console.print("[yellow]Skipping Neo4j start - risolvere conflitto manualmente.[/]")
                    return

        compose_path = self.project_root / "docker-compose.yml"
        if not compose_path.exists():
            self._write_minimal_compose(compose_path)

        # Ensure password is set in compose or via env
        env = os.environ.copy()
        env["NEO4J_AUTH"] = f"neo4j/{self.config.get('NEO4J_PASSWORD','')}"
        cmd = ["docker", "compose", "up", "-d", "neo4j"]

        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            p.add_task(description="Avvio container neo4j...", total=None)
            r = run_cmd(cmd, cwd=self.project_root, env=env, timeout=120)

        if r.returncode == 0:
            console.print("[green]✓[/] Neo4j avviato.")
            console.print("[dim]Attendo 10s per startup...[/]")
            time.sleep(10)
            console.print("[dim]Neo4j Browser: http://localhost:7474[/]")
        else:
            console.print("[red]✗ Avvio fallito[/]")
            console.print(r.stderr[:400])

        console.print()

    def _check_port_conflict(self, port: int) -> bool:
        """Check if a port is already in use."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0

    def _find_neo4j_containers(self) -> List[str]:
        """Find any running Neo4j-related containers."""
        try:
            r = run_cmd(["docker", "ps", "--format", "{{.Names}}"], timeout=10)
            if r.returncode == 0 and r.stdout:
                containers = r.stdout.strip().split('\n')
                return [c for c in containers if 'neo4j' in c.lower() or 'kg-' in c.lower()]
        except Exception:
            pass
        return []

    def _check_neo4j_volumes(self) -> List[str]:
        """Check if Neo4j volumes already exist."""
        try:
            r = run_cmd(["docker", "volume", "ls", "--format", "{{.Name}}"], timeout=10)
            if r.returncode == 0 and r.stdout:
                volumes = r.stdout.strip().split('\n')
                return [v for v in volumes if 'neo4j' in v.lower() or 'kg-mcp' in v.lower()]
        except Exception:
            pass
        return []

    def _write_minimal_compose(self, path: Path) -> None:
        pw = self.config.get("NEO4J_PASSWORD", "neo4j")
        # Note: removed 'version' attribute as it's obsolete in modern docker compose
        content = f"""services:
  neo4j:
    image: neo4j:5
    container_name: kg-neo4j
    restart: always
    environment:
      - NEO4J_AUTH=neo4j/{pw}
      - NEO4J_server_memory_pagecache_size=512M
      - NEO4J_server_memory_heap_initial__size=512M
      - NEO4J_server_memory_heap_max__size=1024M
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
volumes:
  neo4j_data:
  neo4j_logs:
"""
        safe_write_text(path, content)
        console.print(f"[green]✓[/] Creato docker-compose.yml minimale: {path}")

    def _get_container_status(self, container_name: str) -> str:
        """Get the status of a Docker container."""
        try:
            r = run_cmd(["docker", "inspect", "--format", "{{.State.Status}}", container_name], timeout=10)
            if r.returncode == 0 and r.stdout:
                return r.stdout.strip()
            return "not_found"
        except Exception:
            return "unknown"

    def _get_container_health(self, container_name: str) -> str:
        """Get the health status of a Docker container."""
        try:
            r = run_cmd(["docker", "inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}", container_name], timeout=10)
            if r.returncode == 0 and r.stdout:
                return r.stdout.strip()
            return "unknown"
        except Exception:
            return "unknown"

    def _show_docker_logs(self, container_name: str) -> None:
        """Show last few lines of Docker container logs."""
        console.print()
        console.print(Panel(
            "[bold]📋 Docker Logs (ultime 20 righe)[/]",
            border_style="red"
        ))
        try:
            r = run_cmd(["docker", "logs", "--tail", "20", container_name], timeout=10)
            if r.stdout:
                console.print(f"[dim]{r.stdout[:1000]}[/]")
            if r.stderr:
                console.print(f"[red]{r.stderr[:500]}[/]")
        except Exception as e:
            console.print(f"[red]Impossibile ottenere i log: {e}[/]")
        console.print()

    def _show_docker_troubleshooting(self) -> None:
        """Show troubleshooting guide for Docker issues."""
        console.print()
        console.print(Panel(
            "[bold red]⚠️ Troubleshooting Docker[/]\n\n"
            "[bold]1. Verifica che Docker sia in esecuzione:[/]\n"
            "   [cyan]docker info[/]\n\n"
            "[bold]2. Prova ad avviare manualmente:[/]\n"
            f"   [cyan]cd {self.project_root} && docker compose up -d neo4j[/]\n\n"
            "[bold]3. Controlla i container:[/]\n"
            "   [cyan]docker ps -a | grep neo4j[/]\n\n"
            "[bold]4. Vedi i log:[/]\n"
            "   [cyan]docker logs kg-neo4j[/]\n\n"
            "[dim]Se il problema persiste, prova a riavviare Docker Desktop.[/]",
            title="🔧 Come risolvere",
            border_style="yellow"
        ))
        console.print()

    # -------------------------
    # Optional: apply schema
    # -------------------------
    def _optional_apply_schema(self) -> None:
        if self.config.get("NEO4J_APPLY_SCHEMA") != "1":
            return

        console.print(Panel("[bold]Step 6: Apply Neo4j schema (opzionale)[/]", border_style="blue"))

        # Wait for Neo4j to be ready if we just started Docker
        if self.config.get("NEO4J_DOCKER_AUTOSTART") == "1":
            console.print("[dim]Attendo che Neo4j sia pronto (può richiedere fino a 90s)...[/]")
            neo4j_ready = False
            container_status = "unknown"
            
            for attempt in range(45):  # Max 90 seconds (45 * 2s)
                # Check container status AND health
                container_status = self._get_container_status("kg-neo4j")
                health_status = self._get_container_health("kg-neo4j")
                
                if container_status == "not_found":
                    console.print("[red]✗[/] Container kg-neo4j non trovato!")
                    self._show_docker_troubleshooting()
                    break
                elif container_status == "exited":
                    console.print("[red]✗[/] Container kg-neo4j è crashato!")
                    self._show_docker_logs("kg-neo4j")
                    break
                elif container_status == "running":
                    # Check if healthy (Docker health check)
                    if health_status == "healthy":
                        neo4j_ready = True
                        console.print("[green]✓[/] Neo4j è healthy e pronto.")
                        break
                    elif health_status == "unhealthy":
                        console.print("[red]✗[/] Neo4j è unhealthy!")
                        self._show_docker_logs("kg-neo4j")
                        break
                    # If no health check or starting, try port
                    elif health_status in ("none", "starting"):
                        try:
                            import socket
                            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            sock.settimeout(2)
                            result = sock.connect_ex(('localhost', 7687))
                            sock.close()
                            if result == 0:
                                time.sleep(5)  # Extra time for Neo4j to fully initialize
                                neo4j_ready = True
                                console.print("[green]✓[/] Neo4j è pronto.")
                                break
                        except Exception:
                            pass
                
                time.sleep(2)
                if attempt % 5 == 0 and attempt > 0:
                    status_str = f"container: {container_status}"
                    if health_status not in ("none", "unknown"):
                        status_str += f", health: {health_status}"
                    console.print(f"[dim]  ...ancora in attesa ({attempt * 2}s) - {status_str}[/]")
            
            if not neo4j_ready and container_status == "running":
                console.print("[yellow]![/] Neo4j non risponde dopo 90s.")
                self._show_docker_logs("kg-neo4j")
                console.print("[yellow]Provo comunque ad applicare lo schema...[/]")

        # Try running module if present
        server_dir = self.project_root / "server"
        cwd = server_dir if server_dir.exists() else self.project_root

        env = os.environ.copy()
        for k in ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]:
            if k in self.config:
                env[k] = self.config[k]
        
        # Add server/src to PYTHONPATH so kg_mcp is found
        src_dir = server_dir / "src"
        if src_dir.exists():
             current_path = env.get("PYTHONPATH", "")
             env["PYTHONPATH"] = f"{src_dir.absolute()}{os.pathsep}{current_path}"

        cmd = [sys.executable, "-m", "kg_mcp.kg.apply_schema"]

        with Progress(SpinnerColumn(), TextColumn("{task.description}"), console=console) as p:
            p.add_task(description="Applico schema...", total=None)
            try:
                r = run_cmd(cmd, cwd=cwd, env=env, timeout=120)
                if r.returncode == 0:
                    console.print("[green]✓[/] Schema applicato.")
                else:
                    console.print("[yellow]![/] apply_schema ha restituito errori:")
                    # Show complete stderr/stdout for debugging
                    error_output = r.stderr or r.stdout or ""
                    console.print(f"[dim]{error_output}[/]")
                    # Show connection info for debugging
                    pwd_debug = env.get('NEO4J_PASSWORD', '')[:4] + '***' if env.get('NEO4J_PASSWORD') else 'NOT SET'
                    console.print(f"\n[dim]Debug: NEO4J_URI={env.get('NEO4J_URI')}, NEO4J_USER={env.get('NEO4J_USER')}, NEO4J_PASSWORD={pwd_debug}[/]")
                    console.print(f"[dim]Debug: Password in config: {'YES' if 'NEO4J_PASSWORD' in self.config else 'NO'}[/]")
            except Exception as e:
                console.print("[yellow]![/] Impossibile eseguire apply_schema (modulo mancante o errore runtime).")
                console.print(str(e))

        console.print()

    # -------------------------
    # Optional: Antigravity config
    # -------------------------
    def _optional_antigravity(self) -> None:
        if not Confirm.ask("Vuoi aggiornare Antigravity MCP config?", default=True):
            return

        console.print(Panel("[bold]Step 7: Antigravity MCP config[/]", border_style="blue"))

        cfg_path = Path.home() / ".gemini" / "antigravity" / "mcp_config.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)

        existing: Dict[str, Any] = {}
        if cfg_path.exists():
            try:
                existing = json.loads(cfg_path.read_text(encoding="utf-8"))
            except Exception:
                existing = {}

        # Determine python command to run kg_mcp (prefer venv if exists)
        venv_python = self.project_root / "server" / ".venv" / ("Scripts" if sys.platform.startswith("win") else "bin") / ("python.exe" if sys.platform.startswith("win") else "python")
        python_cmd = str(venv_python) if venv_python.exists() else sys.executable

        # Build env for server execution via stdio
        env = {
            "LOG_LEVEL": self.config.get("LOG_LEVEL", "INFO"),
            "KG_MCP_TOKEN": self.config.get("KG_MCP_TOKEN", ""),
            "LLM_MODE": self.config.get("LLM_MODE", ""),
            "LLM_PRIMARY": self.config.get("LLM_PRIMARY", ""),
            "LLM_PROVIDER": self.config.get("LLM_PROVIDER", ""),
            "LLM_MODEL": self.config.get("LLM_MODEL", ""),
        }

        # LLM vars
        for k in [
            "GEMINI_API_KEY",
            "GEMINI_MODEL",
            "GEMINI_BASE_URL",
            "LITELLM_BASE_URL",
            "LITELLM_API_KEY",
            "LITELLM_MODEL",
            "KG_MODEL_DEFAULT",
            "KG_MODEL_FAST",
            "KG_MODEL_REASON",
        ]:
            if k in self.config and self.config[k] != "":
                env[k] = self.config[k]

        # Neo4j vars
        for k in ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]:
            if k in self.config and self.config[k] != "":
                env[k] = self.config[k]

        server_cfg = {
            "command": python_cmd,
            "args": ["-m", "kg_mcp", "--transport", "stdio"],
            "env": env,
        }

        if "mcpServers" not in existing or not isinstance(existing["mcpServers"], dict):
            existing["mcpServers"] = {}
        existing["mcpServers"]["kg-memory"] = server_cfg

        backup_file(cfg_path)
        safe_write_text(cfg_path, json.dumps(existing, indent=2))
        console.print(f"[green]✓[/] Aggiornato: {cfg_path}")

        console.print("\n[bold]In Antigravity:[/]")
        console.print("1) Apri sidebar Agent → MCP Servers")
        console.print("2) Manage/Refresh")
        console.print("3) Dovresti vedere 'kg-memory'\n")

    # -------------------------
    # Summary
    # -------------------------
    def _summary(self) -> None:
        console.print(Panel("[bold green]✓ Setup completato[/]", border_style="green"))

        table = Table(title="Riepilogo", show_header=True, header_style="bold cyan")
        table.add_column("Chiave", style="cyan")
        table.add_column("Valore", style="green")

        # show key info
        show_keys = [
            "LLM_MODE",
            "LLM_PRIMARY",
            "LLM_PROVIDER",
            "LLM_MODEL",
            "GEMINI_MODEL",
            "LITELLM_MODEL",
            "NEO4J_URI",
            "MCP_HOST",
            "MCP_PORT",
            "LOG_LEVEL",
            "KG_MCP_TOKEN",
            "ENV_PATH",
        ]

        temp = dict(self.config)
        temp["ENV_PATH"] = str(self.env_path)

        for k in show_keys:
            if k not in temp or temp[k] == "":
                continue
            v = temp[k]
            if "KEY" in k or "PASSWORD" in k or "TOKEN" in k:
                v = mask(v, keep=6)
            table.add_row(k, v)

        console.print(table)

        # Neo4j Quick Start Tutorial
        if self.config.get("NEO4J_CONFIGURED") == "1":
            neo4j_pass = self.config.get("NEO4J_PASSWORD", "")
            console.print()
            console.print(Panel(
                "[bold cyan]📊 Neo4j Browser - Visualizza il Knowledge Graph[/]\n\n"
                f"[bold]URL:[/] [link=http://localhost:7474]http://localhost:7474[/link]\n"
                f"[bold]User:[/] neo4j\n"
                f"[bold]Password:[/] {neo4j_pass}\n\n"
                "[bold]Query per vedere il grafo:[/]\n"
                "[cyan]MATCH (n)-\[r]->(m) RETURN n, r, m LIMIT 100[/]\n\n"
                "[dim]Copia la query sopra nel Neo4j Browser per visualizzare tutti i nodi e relazioni![/]",
                title="🔗 Quick Start",
                border_style="cyan"
            ))

        # Antigravity restart reminder
        console.print()
        console.print(Panel(
            "[bold yellow]⚠️ Se Antigravity era già aperto:[/]\n\n"
            "1. Chiudi completamente Antigravity\n"
            "2. Riaprilo per caricare la nuova configurazione MCP\n\n"
            "[dim]Oppure: Agent sidebar → MCP Servers → Manage → Refresh[/]",
            title="🔄 Attiva KG-Memory",
            border_style="yellow"
        ))

        console.print(f"\n[bold]File .env:[/] {self.env_path}\n")


def main():
    """Entry point for kg-mcp-setup command."""
    try:
        SetupWizard().run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrotto dall'utente.[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
