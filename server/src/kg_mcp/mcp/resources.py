"""
MCP Resource definitions for the Knowledge Graph Memory Server.
Resources provide read-only access to graph data.
"""

import logging
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP

from kg_mcp.kg.repo import get_repository

logger = logging.getLogger(__name__)


def register_resources(mcp: FastMCP) -> None:
    """Register all MCP resources with the server."""

    @mcp.resource("kg://projects/{project_id}/active-goals")
    async def get_active_goals(project_id: str) -> str:
        """
        Get all active goals for a project.

        Returns a Markdown-formatted list of active goals with their
        acceptance criteria, constraints, and strategies.
        """
        logger.info(f"Resource requested: active-goals for project {project_id}")

        try:
            repo = get_repository()
            goals = await repo.get_active_goals(project_id)

            if not goals:
                return f"# Active Goals for {project_id}\n\nNo active goals found."

            lines = [f"# Active Goals for {project_id}\n"]

            for i, goal in enumerate(goals, 1):
                priority = goal.get("priority", 3)
                emoji = {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "⚪"}.get(priority, "⚪")

                lines.append(f"## {i}. {emoji} {goal.get('title', 'Untitled')}")
                lines.append(f"**ID:** `{goal.get('id', 'N/A')}`")
                lines.append(f"**Priority:** {priority}")

                if goal.get("description"):
                    lines.append(f"\n{goal['description']}")

                if goal.get("acceptance_criteria"):
                    lines.append("\n**Acceptance Criteria:**")
                    for ac in goal["acceptance_criteria"]:
                        criterion = ac.get("criterion", ac) if isinstance(ac, dict) else ac
                        lines.append(f"- [ ] {criterion}")

                if goal.get("constraints"):
                    lines.append("\n**Constraints:**")
                    for c in goal["constraints"]:
                        if isinstance(c, dict) and c:
                            lines.append(f"- [{c.get('severity', 'must')}] {c.get('description', '')}")

                if goal.get("strategies"):
                    lines.append("\n**Strategies:**")
                    for s in goal["strategies"]:
                        if isinstance(s, dict) and s:
                            lines.append(f"- {s.get('title', 'Strategy')}: {s.get('approach', '')}")

                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to get active goals: {e}")
            return f"# Error\n\nFailed to retrieve active goals: {e}"

    @mcp.resource("kg://projects/{project_id}/preferences")
    async def get_preferences(project_id: str) -> str:
        """
        Get user preferences for a project.

        Returns coding style preferences, architectural preferences,
        tool preferences, and output format preferences.
        """
        logger.info(f"Resource requested: preferences for project {project_id}")

        try:
            repo = get_repository()
            # Use default_user for now; could be parameterized
            preferences = await repo.get_preferences("default_user")

            if not preferences:
                return f"# Preferences for {project_id}\n\nNo preferences configured."

            lines = [f"# Preferences for {project_id}\n"]

            # Group by category
            by_category: Dict[str, List[Dict[str, Any]]] = {}
            for pref in preferences:
                cat = pref.get("category", "other")
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(pref)

            for category, prefs in by_category.items():
                lines.append(f"## {category.replace('_', ' ').title()}\n")
                for p in prefs:
                    strength = p.get("strength", "prefer")
                    prefix = {
                        "require": "✅ REQUIRE",
                        "avoid": "❌ AVOID",
                        "prefer": "💡 PREFER",
                    }.get(strength, "💡")
                    lines.append(f"- {prefix}: {p.get('preference', '')}")
                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to get preferences: {e}")
            return f"# Error\n\nFailed to retrieve preferences: {e}"

    @mcp.resource("kg://projects/{project_id}/goal/{goal_id}/subgraph")
    async def get_goal_subgraph(project_id: str, goal_id: str) -> str:
        """
        Get the subgraph around a specific goal.

        Returns the goal and all entities connected within 2 hops:
        constraints, strategies, pain points, code artifacts, tests.
        """
        logger.info(f"Resource requested: subgraph for goal {goal_id}")

        try:
            repo = get_repository()
            subgraph = await repo.get_goal_subgraph(goal_id, k_hops=2)

            if not subgraph.get("goal"):
                return f"# Goal Subgraph\n\nGoal `{goal_id}` not found."

            goal = subgraph["goal"]
            connected = subgraph.get("connected", [])

            lines = [
                f"# Goal: {goal.get('title', 'Untitled')}",
                f"**ID:** `{goal_id}`",
                f"**Status:** {goal.get('status', 'unknown')}",
                f"**Priority:** {goal.get('priority', '-')}",
            ]

            if goal.get("description"):
                lines.append(f"\n{goal['description']}")

            if connected:
                lines.append(f"\n## Connected Entities ({len(connected)} total)\n")

                # Categorize connected nodes
                for node in connected:
                    if isinstance(node, dict):
                        # Try to identify node type by properties
                        if "approach" in node:
                            lines.append(f"- **Strategy:** {node.get('title', 'Untitled')}")
                        elif "severity" in node and "description" in node:
                            lines.append(f"- **PainPoint:** {node.get('description', '')[:50]}...")
                        elif "path" in node:
                            lines.append(f"- **CodeArtifact:** `{node.get('path', '')}`")
                        elif "criterion" in node:
                            lines.append(f"- **AcceptanceCriteria:** {node.get('criterion', '')}")
                        else:
                            lines.append(f"- **Entity:** {node}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to get goal subgraph: {e}")
            return f"# Error\n\nFailed to retrieve goal subgraph: {e}"

    @mcp.resource("kg://projects/{project_id}/pain-points")
    async def get_pain_points(project_id: str) -> str:
        """
        Get open pain points for a project.

        Returns unresolved pain points sorted by severity.
        """
        logger.info(f"Resource requested: pain-points for project {project_id}")

        try:
            repo = get_repository()
            pain_points = await repo.get_open_painpoints(project_id)

            if not pain_points:
                return f"# Open Pain Points for {project_id}\n\n✅ No open pain points!"

            lines = [f"# Open Pain Points for {project_id}\n"]

            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢",
            }

            for pp in pain_points:
                severity = pp.get("severity", "medium")
                emoji = severity_emoji.get(severity, "⚪")
                lines.append(f"## {emoji} [{severity.upper()}] Pain Point")
                lines.append(f"**ID:** `{pp.get('id', 'N/A')}`")
                lines.append(f"\n{pp.get('description', 'No description')}")

                if pp.get("blocking_goals"):
                    lines.append(f"\n**Blocking Goals:** {', '.join(pp['blocking_goals'])}")

                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"Failed to get pain points: {e}")
            return f"# Error\n\nFailed to retrieve pain points: {e}"

    logger.info("MCP resources registered successfully")
