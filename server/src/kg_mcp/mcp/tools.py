"""
MCP Tool definitions for the Knowledge Graph Memory Server.
These are the main entry points for IDE agents to interact with the KG.
"""

import logging
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from kg_mcp.kg.ingest import get_ingest_pipeline
from kg_mcp.kg.retrieval import get_context_builder
from kg_mcp.kg.repo import get_repository
from kg_mcp.utils import serialize_response

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Input/Output Schemas
# =============================================================================


class IngestMessageInput(BaseModel):
    """Input schema for kg_ingest_message tool."""

    project_id: str = Field(..., description="Unique identifier for the project")
    user_text: str = Field(..., description="The user's message or request text")
    files: Optional[List[str]] = Field(
        None, description="List of file paths involved in this request"
    )
    diff: Optional[str] = Field(None, description="Code diff if available")
    symbols: Optional[List[str]] = Field(
        None, description="List of code symbols referenced"
    )
    tags: Optional[List[str]] = Field(
        None, description="Tags to categorize this interaction"
    )


class ContextPackInput(BaseModel):
    """Input schema for kg_context_pack tool."""

    project_id: str = Field(..., description="Project to build context for")
    focus_goal_id: Optional[str] = Field(
        None, description="Specific goal ID to focus the context on"
    )
    query: Optional[str] = Field(
        None, description="Optional search query for additional context"
    )
    k_hops: int = Field(
        default=2, ge=1, le=5, description="Number of hops for graph traversal"
    )


class SearchInput(BaseModel):
    """Input schema for kg_search tool."""

    project_id: str = Field(..., description="Project to search within")
    query: str = Field(..., description="Search query")
    filters: Optional[List[str]] = Field(
        None,
        description="Filter by node types: Goal, PainPoint, Strategy, Decision, CodeArtifact",
    )
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results to return")


class LinkCodeArtifactInput(BaseModel):
    """Input schema for kg_link_code_artifact tool."""

    project_id: str = Field(..., description="Project ID")
    path: str = Field(..., description="File path of the artifact")
    kind: str = Field(
        default="file",
        description="Type: file, function, class, snippet",
    )
    language: Optional[str] = Field(None, description="Programming language")
    symbol_fqn: Optional[str] = Field(
        None, description="Fully qualified name of the symbol"
    )
    start_line: Optional[int] = Field(None, description="Start line number")
    end_line: Optional[int] = Field(None, description="End line number")
    git_commit: Optional[str] = Field(None, description="Git commit hash")
    content_hash: Optional[str] = Field(None, description="Hash of the content")
    related_goal_ids: Optional[List[str]] = Field(
        None, description="IDs of goals this artifact implements"
    )


class ImpactAnalysisInput(BaseModel):
    """Input schema for kg_impact_analysis tool."""

    project_id: str = Field(..., description="Project ID")
    changed_paths: Optional[List[str]] = Field(
        None, description="List of changed file paths"
    )
    changed_symbols: Optional[List[str]] = Field(
        None, description="List of changed symbol FQNs"
    )


# =============================================================================
# Tool Registration
# =============================================================================


def register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools with the server."""

    @mcp.tool()
    async def kg_ingest_message(
        project_id: str,
        user_text: str,
        files: Optional[List[str]] = None,
        diff: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze and save a user request to the knowledge graph.

        This tool:
        1. Creates an Interaction node for the request
        2. Uses LLM to extract goals, constraints, preferences, pain points, strategies
        3. Links entities with existing graph nodes (deduplication + relationships)
        4. Commits everything to Neo4j

        Call this at the START of every coding task to build context.

        Args:
            project_id: Unique identifier for the project/workspace
            user_text: The user's message or request
            files: Optional list of file paths involved
            diff: Optional code diff
            symbols: Optional list of code symbols (function names, classes)
            tags: Optional tags for categorization

        Returns:
            interaction_id: ID of the created interaction
            extracted: Extracted entities (goals, constraints, etc.)
            created_entities: IDs of created/updated entities
            confidence: Extraction confidence score
        """
        logger.info(f"kg_ingest_message called for project {project_id}")

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
            logger.error(f"kg_ingest_message failed: {e}")
            return {
                "error": str(e),
                "interaction_id": None,
                "extracted": {},
                "created_entities": {},
            }

    @mcp.tool()
    async def kg_context_pack(
        project_id: str,
        focus_goal_id: Optional[str] = None,
        query: Optional[str] = None,
        k_hops: int = 2,
    ) -> Dict[str, Any]:
        """
        Build a comprehensive context pack from the knowledge graph.

        This retrieves:
        - Active goals with acceptance criteria, constraints, strategies
        - User preferences and coding style guidelines
        - Open pain points and blockers
        - Relevant code artifacts
        - Search results if query is provided

        Call this AFTER kg_ingest_message to get context for your task.

        Args:
            project_id: Project to build context for
            focus_goal_id: Optional specific goal to focus on
            query: Optional search query for additional relevant context
            k_hops: Depth of graph traversal (1-5, default 2)

        Returns:
            markdown: Formatted context in Markdown (ready to use as system context)
            entities: Raw entity data for programmatic access
        """
        logger.info(f"kg_context_pack called for project {project_id}")

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
            logger.error(f"kg_context_pack failed: {e}")
            return {
                "error": str(e),
                "markdown": f"# Error\n\nFailed to build context: {e}",
                "entities": {},
            }

    @mcp.tool()
    async def kg_search(
        project_id: str,
        query: str,
        filters: Optional[List[str]] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Search the knowledge graph using fulltext + traversal.

        Searches across goals, pain points, strategies, decisions, and code artifacts.

        Args:
            project_id: Project to search within
            query: Search query (supports natural language)
            filters: Optional type filters (Goal, PainPoint, Strategy, Decision, CodeArtifact)
            limit: Maximum results (default 20, max 100)

        Returns:
            results: List of matching entities with scores
            total: Total number of matches
        """
        logger.info(f"kg_search called: '{query}' in project {project_id}")

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
            logger.error(f"kg_search failed: {e}")
            return {
                "error": str(e),
                "results": [],
                "total": 0,
            }

    @mcp.tool()
    async def kg_link_code_artifact(
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
        Link a code artifact to the knowledge graph.

        Call this when you CREATE or MODIFY a file to keep the graph updated.
        This enables impact analysis and goal-code traceability.

        Args:
            project_id: Project ID
            path: File path (relative or absolute)
            kind: Type: file, function, class, snippet
            language: Programming language (python, typescript, etc.)
            symbol_fqn: Fully qualified name (e.g., 'module.ClassName.method_name')
            start_line: Start line for the symbol
            end_line: End line for the symbol
            git_commit: Current git commit hash
            content_hash: Hash of the file content
            related_goal_ids: Goal IDs this artifact implements

        Returns:
            artifact_id: ID of the created/updated artifact
            symbol_id: ID of the symbol (if symbol_fqn provided)
            linked_goals: Number of goals linked
        """
        logger.info(f"kg_link_code_artifact called: {path}")

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
            logger.error(f"kg_link_code_artifact failed: {e}")
            return {
                "error": str(e),
                "artifact_id": None,
            }

    @mcp.tool()
    async def kg_impact_analysis(
        project_id: str,
        changed_paths: Optional[List[str]] = None,
        changed_symbols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze the impact of code changes.

        Given changed files or symbols, returns:
        - Goals that might be affected
        - Tests that should be run
        - Strategies that may need review
        - Related artifacts

        Use this before making changes to understand the scope of impact.

        Args:
            project_id: Project ID
            changed_paths: List of file paths that changed
            changed_symbols: List of symbol FQNs that changed

        Returns:
            goals_to_retest: Goals that may be affected by these changes
            tests_to_run: Test cases that should be executed
            strategies_to_review: Strategies that may need updating
            artifacts_related: Other related code artifacts
        """
        logger.info(f"kg_impact_analysis called for project {project_id}")

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
            logger.error(f"kg_impact_analysis failed: {e}")
            return {
                "error": str(e),
                "goals_to_retest": [],
                "tests_to_run": [],
                "strategies_to_review": [],
                "artifacts_related": [],
            }

    logger.info("MCP tools registered successfully")
