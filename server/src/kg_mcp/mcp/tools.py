"""
MCP Tool definitions for the Knowledge Graph Memory Server.

This module exposes ONLY 2 tools to AI agents:
- kg_autopilot: Call at the START of every task
- kg_track_changes: Call AFTER every file modification

All other functionality is internal and not exposed via MCP.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from kg_mcp.kg.ingest import get_ingest_pipeline
from kg_mcp.kg.retrieval import get_context_builder
from kg_mcp.kg.repo import get_repository
from kg_mcp.utils import serialize_response

logger = logging.getLogger(__name__)


# =============================================================================
# INTERNAL HELPER FUNCTIONS (Not exposed via MCP)
# =============================================================================


async def _ingest_message(
    project_id: str,
    user_text: str,
    files: Optional[List[str]] = None,
    diff: Optional[str] = None,
    symbols: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Internal: Analyze and save a user request to the knowledge graph.
    Called by kg_autopilot.
    """
    logger.info(f"_ingest_message called for project {project_id}")

    try:
        pipeline = get_ingest_pipeline()
        result = await pipeline.process_message(
            project_id=project_id,
            user_text=user_text,
            files=files,
            diff=diff,
            symbols=symbols,
            tags=tags,
        )
        return serialize_response(result)
    except Exception as e:
        logger.error(f"_ingest_message failed: {e}")
        return {
            "error": str(e),
            "interaction_id": None,
            "extracted": {},
            "created_entities": {},
        }


async def _context_pack(
    project_id: str,
    focus_goal_id: Optional[str] = None,
    query: Optional[str] = None,
    k_hops: int = 2,
) -> Dict[str, Any]:
    """
    Internal: Build a comprehensive context pack from the knowledge graph.
    Called by kg_autopilot.
    """
    logger.info(f"_context_pack called for project {project_id}")

    try:
        builder = get_context_builder()
        result = await builder.build_context_pack(
            project_id=project_id,
            focus_goal_id=focus_goal_id,
            query=query,
            k_hops=k_hops,
        )
        return serialize_response(result)
    except Exception as e:
        logger.error(f"_context_pack failed: {e}")
        return {
            "error": str(e),
            "markdown": f"# Error\n\nFailed to build context: {e}",
            "entities": {},
        }


async def _search(
    project_id: str,
    query: str,
    filters: Optional[List[str]] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Internal: Search the knowledge graph using fulltext + traversal.
    Called by kg_autopilot when search_query is provided.
    """
    logger.info(f"_search called: '{query}' in project {project_id}")

    try:
        repo = get_repository()
        results = await repo.fulltext_search(
            project_id=project_id,
            query=query,
            node_types=filters,
            limit=limit,
        )
        return serialize_response({
            "results": results,
            "total": len(results),
            "query": query,
        })
    except Exception as e:
        logger.error(f"_search failed: {e}")
        return {
            "error": str(e),
            "results": [],
            "total": 0,
        }


async def _link_code_artifact(
    project_id: str,
    path: str,
    kind: str = "file",
    language: Optional[str] = None,
    symbol_fqn: Optional[str] = None,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    git_commit: Optional[str] = None,
    content_hash: Optional[str] = None,
    related_goal_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Internal: Link a code artifact to the knowledge graph.
    Called by kg_track_changes.
    """
    logger.info(f"_link_code_artifact called: {path}")

    try:
        repo = get_repository()
        artifact = await repo.upsert_code_artifact(
            project_id=project_id,
            path=path,
            kind=kind,
            language=language,
            symbol_fqn=symbol_fqn,
            start_line=start_line,
            end_line=end_line,
            git_commit=git_commit,
            content_hash=content_hash,
            related_goal_ids=related_goal_ids,
        )
        return {
            "artifact_id": artifact.get("id"),
            "path": path,
            "linked_goals": len(related_goal_ids) if related_goal_ids else 0,
        }
    except Exception as e:
        logger.error(f"_link_code_artifact failed: {e}")
        return {
            "error": str(e),
            "artifact_id": None,
        }


async def _impact_analysis(
    project_id: str,
    changed_paths: Optional[List[str]] = None,
    changed_symbols: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Internal: Analyze the impact of code changes.
    Called by kg_track_changes when check_impact=True.
    """
    logger.info(f"_impact_analysis called for project {project_id}")

    if not changed_paths and not changed_symbols:
        return {
            "error": "At least one of changed_paths or changed_symbols is required",
            "goals_to_retest": [],
            "tests_to_run": [],
            "strategies_to_review": [],
            "artifacts_related": [],
        }

    try:
        repo = get_repository()
        paths = changed_paths or []

        result = await repo.get_impact_for_artifacts(project_id, paths)
        return serialize_response(result)
    except Exception as e:
        logger.error(f"_impact_analysis failed: {e}")
        return {
            "error": str(e),
            "goals_to_retest": [],
            "tests_to_run": [],
            "strategies_to_review": [],
            "artifacts_related": [],
        }


# =============================================================================
# MCP TOOL REGISTRATION (Only 2 tools exposed)
# =============================================================================


def register_tools(mcp: FastMCP) -> None:
    """
    Register MCP tools with the server.
    
    Only 2 tools are exposed:
    - kg_autopilot: For starting tasks
    - kg_track_changes: For tracking file modifications
    """

    @mcp.tool()
    async def kg_autopilot(
        project_id: str,
        user_text: str,
        search_query: Optional[str] = None,
        files: Optional[List[str]] = None,
        diff: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        k_hops: int = 2,
    ) -> Dict[str, Any]:
        """
        🚀 CALL THIS TOOL AT THE START OF EVERY TASK.

        ⚠️ DO NOT CALL THIS TOOL AFTER CREATING/MODIFYING FILES!
        Use kg_track_changes instead for file changes.

        WHEN TO USE THIS TOOL:
        ✅ Starting a new task or user request
        ✅ User asks a question (to retrieve past context)
        ✅ Resuming work on an existing project
        ✅ Need to understand goals, constraints, preferences

        WHEN NOT TO USE THIS TOOL:
        ❌ After creating a file → use kg_track_changes
        ❌ After modifying a file → use kg_track_changes
        ❌ To "save" or "record" task completion → NOT NEEDED
        ❌ To update goal status → NOT SUPPORTED HERE

        It automatically:
        1. Ingests and analyzes the user request (extracts goals, constraints, etc.)
        2. Returns the full context pack with active goals, preferences, pain points
        3. Optionally searches existing knowledge if search_query is provided

        Args:
            project_id: Project identifier (use workspace folder name)
            user_text: The user's message or request
            search_query: Optional query to search existing knowledge
            files: Optional list of file paths involved
            diff: Optional code diff
            symbols: Optional list of code symbols
            tags: Optional tags for categorization
            k_hops: Graph traversal depth (1-5, default 2)

        Returns:
            markdown: Formatted context pack (READ THIS CAREFULLY)
            interaction_id: ID of the ingested interaction
            extracted: Extracted entities (goals, constraints, etc.)
            search_results: Search results if search_query was provided
        """
        logger.info(f"kg_autopilot called for project {project_id}")

        result: Dict[str, Any] = {
            "markdown": "",
            "interaction_id": None,
            "extracted": {},
            "search_results": [],
        }

        try:
            # Step 1: Ingest the message
            pipeline = get_ingest_pipeline()
            ingest_result = await pipeline.process_message(
                project_id=project_id,
                user_text=user_text,
                files=files,
                diff=diff,
                symbols=symbols,
                tags=tags,
            )
            result["interaction_id"] = ingest_result.get("interaction_id")
            result["extracted"] = ingest_result.get("extracted", {})

            # Step 2: Build context pack
            builder = get_context_builder()
            context_result = await builder.build_context_pack(
                project_id=project_id,
                query=search_query,
                k_hops=k_hops,
            )
            result["markdown"] = context_result.get("markdown", "")
            # Add reminder about kg_track_changes
            result["markdown"] += "\n\n---\n*📝 REMINDER: Call `kg_track_changes` after EVERY file you create or modify to keep the knowledge graph updated.*"
            result["entities"] = context_result.get("entities", {})

            # Step 3: Optional search
            if search_query:
                repo = get_repository()
                search_results = await repo.fulltext_search(
                    project_id=project_id,
                    query=search_query,
                    limit=10,
                )
                result["search_results"] = search_results

            return serialize_response(result)

        except Exception as e:
            logger.error(f"kg_autopilot failed: {e}")
            result["error"] = str(e)
            result["markdown"] = f"# Error\n\nFailed to build context: {e}"
            return result

    @mcp.tool()
    async def kg_track_changes(
        project_id: str,
        changed_paths: List[str],
        check_impact: bool = True,
        language: Optional[str] = None,
        related_goal_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        🔗 CALL THIS TOOL AFTER EVERY FILE MODIFICATION.

        ⚠️ DO NOT use kg_autopilot for tracking file changes!

        WHEN TO USE THIS TOOL:
        ✅ After creating a new file (write_to_file tool)
        ✅ After modifying a file (replace_file_content, multi_replace tools)
        ✅ After deleting a file
        ✅ After refactoring operations

        WHEN NOT TO USE THIS TOOL:
        ❌ At the start of a task → use kg_autopilot
        ❌ To retrieve context → use kg_autopilot
        ❌ To ingest user requests → use kg_autopilot

        WHAT THIS TOOL DOES:
        1. Links files to the knowledge graph as CodeArtifact nodes
        2. AUTO-LINKS to ALL active goals (no need to specify goal IDs!)
        3. Runs impact analysis to identify affected goals/tests
        4. Enables future context retrieval (so next session remembers what was done)

        Call it IMMEDIATELY after each file modification, not at the end of your work.

        Args:
            project_id: Project identifier
            changed_paths: List of file paths that were created/modified/deleted (REQUIRED)
            check_impact: Whether to run impact analysis (default: True)
            language: Programming language (auto-detected if not provided)
            related_goal_ids: Optional goal IDs (if None, AUTO-LINKS to all active goals!)

        Returns:
            artifacts_linked: Number of artifacts linked to the graph
            auto_linked_goals: Goals that were automatically linked
            impact_analysis: Goals, tests, and strategies that may be affected
        """
        logger.info(f"kg_track_changes called for {len(changed_paths)} files")

        if not changed_paths:
            return {
                "error": "changed_paths is required and cannot be empty",
                "artifacts_linked": 0,
                "impact_analysis": {},
            }

        result: Dict[str, Any] = {
            "artifacts_linked": 0,
            "linked_paths": [],
            "impact_analysis": {},
        }

        try:
            repo = get_repository()

            # Step 1: Auto-link to active goals if not specified
            auto_linked = False
            if related_goal_ids is None:
                try:
                    active_goals = await repo.get_active_goals(project_id)
                    related_goal_ids = [g["id"] for g in active_goals if g.get("id")]
                    auto_linked = True
                    result["auto_linked_goals"] = [
                        {"id": g["id"], "title": g.get("title", "Unknown")}
                        for g in active_goals if g.get("id")
                    ]
                    logger.info(f"Auto-linking to {len(related_goal_ids)} active goals")
                except Exception as goal_error:
                    logger.warning(f"Could not fetch active goals for auto-linking: {goal_error}")
                    related_goal_ids = []
                    result["auto_linked_goals"] = []
            else:
                result["auto_linked_goals"] = []

            # Step 2: Link all artifacts
            for path in changed_paths:
                try:
                    await repo.upsert_code_artifact(
                        project_id=project_id,
                        path=path,
                        kind="file",
                        language=language,
                        related_goal_ids=related_goal_ids,
                    )
                    result["artifacts_linked"] += 1
                    result["linked_paths"].append(path)
                except Exception as link_error:
                    logger.warning(f"Failed to link {path}: {link_error}")

            # Step 2: Impact analysis
            if check_impact:
                impact = await repo.get_impact_for_artifacts(project_id, changed_paths)
                result["impact_analysis"] = impact

            return serialize_response(result)

        except Exception as e:
            logger.error(f"kg_track_changes failed: {e}")
            result["error"] = str(e)
            return result

    logger.info("MCP tools registered: kg_autopilot, kg_track_changes (2 tools only)")
