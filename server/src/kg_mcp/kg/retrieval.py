"""
Retrieval module for building context packs from the knowledge graph.
Navigates the graph to construct relevant context for IDE agents.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from kg_mcp.kg.repo import get_repository

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds context packs from the knowledge graph."""

    def __init__(self):
        self.repo = get_repository()

    async def build_context_pack(
        self,
        project_id: str,
        focus_goal_id: Optional[str] = None,
        query: Optional[str] = None,
        k_hops: int = 2,
        user_id: str = "default_user",
    ) -> Dict[str, Any]:
        """
        Build a comprehensive context pack for an IDE agent.

        Args:
            project_id: Project to build context for
            focus_goal_id: Optional specific goal to focus on
            query: Optional search query for additional context
            k_hops: Number of hops for graph traversal
            user_id: User ID for preferences

        Returns:
            Dict with 'markdown' (formatted context) and 'entities' (raw data)
        """
        logger.info(f"Building context pack for project {project_id}")

        entities: Dict[str, Any] = {
            "active_goals": [],
            "preferences": [],
            "constraints": [],
            "pain_points": [],
            "strategies": [],
            "recent_decisions": [],
            "code_artifacts": [],
            "focus_goal_subgraph": None,
            "search_results": [],
        }

        # Get active goals
        entities["active_goals"] = await self.repo.get_active_goals(project_id)
        logger.debug(f"Found {len(entities['active_goals'])} active goals")

        # Get user preferences
        entities["preferences"] = await self.repo.get_preferences(user_id)
        logger.debug(f"Found {len(entities['preferences'])} preferences")

        # Get open pain points
        entities["pain_points"] = await self.repo.get_open_painpoints(project_id)
        logger.debug(f"Found {len(entities['pain_points'])} open pain points")

        # If focus goal specified, get its subgraph
        if focus_goal_id:
            entities["focus_goal_subgraph"] = await self.repo.get_goal_subgraph(
                focus_goal_id, k_hops
            )
            # Get artifacts for the focused goal
            entities["code_artifacts"] = await self.repo.get_artifacts_for_goal(focus_goal_id)

        # If query specified, do fulltext search
        if query:
            entities["search_results"] = await self.repo.fulltext_search(
                project_id=project_id,
                query=query,
                limit=10,
            )

        # Build markdown context
        markdown = self._format_markdown(entities, project_id)

        return {
            "markdown": markdown,
            "entities": entities,
        }

    def _format_markdown(self, entities: Dict[str, Any], project_id: str) -> str:
        """Format entities into a structured markdown document."""
        sections = []

        # Header
        sections.append(f"# 📋 Context Pack for Project: {project_id}")
        sections.append(f"*Generated at: {datetime.utcnow().isoformat()}*\n")

        # Active Goals
        if entities["active_goals"]:
            sections.append("## 🎯 Active Goals\n")
            for i, goal in enumerate(entities["active_goals"], 1):
                priority_emoji = self._priority_emoji(goal.get("priority", 3))
                sections.append(
                    f"### {i}. {priority_emoji} {goal.get('title', 'Untitled')}\n"
                )
                if goal.get("description"):
                    sections.append(f"**Description:** {goal['description']}\n")
                sections.append(f"**Status:** {goal.get('status', 'unknown')}")
                sections.append(f"**Priority:** {goal.get('priority', '-')}\n")

                # Acceptance criteria
                if goal.get("acceptance_criteria"):
                    sections.append("**Acceptance Criteria:**")
                    for ac in goal["acceptance_criteria"]:
                        sections.append(f"- [ ] {ac.get('criterion', ac)}")
                    sections.append("")

                # Constraints
                if goal.get("constraints"):
                    sections.append("**Constraints:**")
                    for c in goal["constraints"]:
                        severity = c.get("severity", "must")
                        sections.append(f"- [{severity}] {c.get('description', c)}")
                    sections.append("")

                # Strategies
                if goal.get("strategies"):
                    sections.append("**Strategies:**")
                    for s in goal["strategies"]:
                        sections.append(f"- **{s.get('title', 'Strategy')}**: {s.get('approach', '')}")
                    sections.append("")

        # User Preferences
        if entities["preferences"]:
            sections.append("## ⚙️ User Preferences\n")
            prefs_by_category: Dict[str, List[Any]] = {}
            for pref in entities["preferences"]:
                cat = pref.get("category", "other")
                if cat not in prefs_by_category:
                    prefs_by_category[cat] = []
                prefs_by_category[cat].append(pref)

            for category, prefs in prefs_by_category.items():
                sections.append(f"**{category.replace('_', ' ').title()}:**")
                for p in prefs:
                    strength = p.get("strength", "prefer")
                    prefix = "✅" if strength == "require" else ("❌" if strength == "avoid" else "💡")
                    sections.append(f"- {prefix} {p.get('preference', p)}")
                sections.append("")

        # Pain Points
        if entities["pain_points"]:
            sections.append("## ⚠️ Open Pain Points\n")
            for pp in entities["pain_points"]:
                severity = pp.get("severity", "medium")
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(
                    severity, "⚪"
                )
                sections.append(f"- {emoji} **[{severity}]** {pp.get('description', pp)}")
                if pp.get("blocking_goals"):
                    sections.append(f"  - Blocking: {', '.join(pp['blocking_goals'])}")
            sections.append("")

        # Code Artifacts
        if entities["code_artifacts"]:
            sections.append("## 📁 Relevant Code Artifacts\n")
            for artifact in entities["code_artifacts"]:
                path = artifact.get("path", "unknown")
                kind = artifact.get("kind", "file")
                sections.append(f"- **{path}** ({kind})")
                if artifact.get("symbols"):
                    for sym in artifact["symbols"][:5]:
                        sections.append(f"  - `{sym.get('fqn', sym.get('name', 'symbol'))}`")
            sections.append("")

        # Focus Goal Subgraph
        if entities.get("focus_goal_subgraph") and entities["focus_goal_subgraph"].get("goal"):
            fg = entities["focus_goal_subgraph"]
            sections.append("## 🔍 Focus Goal Details\n")
            sections.append(f"**Goal:** {fg['goal'].get('title', 'Untitled')}\n")
            if fg.get("connected"):
                sections.append("**Connected entities:**")
                for node in fg["connected"][:10]:
                    if isinstance(node, dict):
                        node_type = list(node.keys())[0] if node else "Entity"
                        sections.append(f"- {node}")
            sections.append("")

        # Search Results
        if entities["search_results"]:
            sections.append("## 🔎 Search Results\n")
            for result in entities["search_results"]:
                rtype = result.get("type", "Unknown")
                data = result.get("data", {})
                score = result.get("score", 0)
                title = data.get("title") or data.get("description", str(data))[:50]
                sections.append(f"- **[{rtype}]** {title} (score: {score:.2f})")
            sections.append("")

        # Footer with instructions
        sections.append("---")
        sections.append(
            "*Use this context to guide your work. "
            "Call `kg_link_code_artifact` when creating/modifying files to keep the graph updated.*"
        )

        return "\n".join(sections)

    def _priority_emoji(self, priority: int) -> str:
        """Convert priority number to emoji."""
        return {1: "🔴", 2: "🟠", 3: "🟡", 4: "🟢", 5: "⚪"}.get(priority, "⚪")


# Factory function
_builder: Optional[ContextBuilder] = None


def get_context_builder() -> ContextBuilder:
    """Get or create the context builder singleton."""
    global _builder
    if _builder is None:
        _builder = ContextBuilder()
    return _builder
