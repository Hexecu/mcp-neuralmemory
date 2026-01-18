"""
Repository layer for Neo4j queries.
Provides typed query functions for CRUD operations on the knowledge graph.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from kg_mcp.kg.neo4j import get_neo4j_client

logger = logging.getLogger(__name__)


class KGRepository:
    """Repository for knowledge graph operations."""

    def __init__(self):
        self.client = get_neo4j_client()

    # =========================================================================
    # Project Operations
    # =========================================================================

    async def get_or_create_project(self, project_id: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Get or create a project node."""
        query = """
        MERGE (p:Project {id: $project_id})
        ON CREATE SET 
            p.name = $name,
            p.created_at = datetime(),
            p.updated_at = datetime()
        ON MATCH SET
            p.updated_at = datetime()
        RETURN p {.*} as project
        """
        result = await self.client.execute_query(
            query,
            {"project_id": project_id, "name": name or project_id},
        )
        return result[0]["project"] if result else {}

    # =========================================================================
    # Interaction Operations
    # =========================================================================

    async def create_interaction(
        self,
        project_id: str,
        user_text: str,
        assistant_text: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new interaction node."""
        interaction_id = str(uuid4())
        query = """
        MATCH (p:Project {id: $project_id})
        CREATE (i:Interaction {
            id: $interaction_id,
            user_text: $user_text,
            assistant_text: $assistant_text,
            tags: $tags,
            project_id: $project_id,
            timestamp: datetime(),
            created_at: datetime()
        })
        CREATE (i)-[:IN_PROJECT]->(p)
        RETURN i {.*} as interaction
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "interaction_id": interaction_id,
                "user_text": user_text,
                "assistant_text": assistant_text,
                "tags": tags or [],
            },
        )
        return result[0]["interaction"] if result else {"id": interaction_id}

    async def get_recent_interactions(
        self, project_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent interactions for a project."""
        query = """
        MATCH (i:Interaction {project_id: $project_id})
        RETURN i {.*} as interaction
        ORDER BY i.timestamp DESC
        LIMIT $limit
        """
        result = await self.client.execute_query(
            query, {"project_id": project_id, "limit": limit}
        )
        return [r["interaction"] for r in result]

    # =========================================================================
    # Goal Operations
    # =========================================================================

    async def upsert_goal(
        self,
        project_id: str,
        title: str,
        description: Optional[str] = None,
        status: str = "active",
        priority: int = 2,
        goal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert a goal node."""
        goal_id = goal_id or str(uuid4())
        query = """
        MATCH (p:Project {id: $project_id})
        MERGE (g:Goal {project_id: $project_id, title: $title})
        ON CREATE SET
            g.id = $goal_id,
            g.description = $description,
            g.status = $status,
            g.priority = $priority,
            g.created_at = datetime(),
            g.updated_at = datetime()
        ON MATCH SET
            g.description = COALESCE($description, g.description),
            g.status = $status,
            g.priority = $priority,
            g.updated_at = datetime()
        MERGE (p)-[:HAS_GOAL]->(g)
        RETURN g {.*} as goal
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "goal_id": goal_id,
                "title": title,
                "description": description,
                "status": status,
                "priority": priority,
            },
        )
        return result[0]["goal"] if result else {"id": goal_id, "title": title}

    async def get_active_goals(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all active goals for a project."""
        query = """
        MATCH (g:Goal {project_id: $project_id, status: 'active'})
        OPTIONAL MATCH (g)-[:HAS_CONSTRAINT]->(c:Constraint)
        OPTIONAL MATCH (g)-[:HAS_STRATEGY]->(s:Strategy)
        OPTIONAL MATCH (g)-[:HAS_ACCEPTANCE_CRITERIA]->(ac:AcceptanceCriteria)
        WITH g, 
             collect(DISTINCT c {.*}) as constraints,
             collect(DISTINCT s {.*}) as strategies,
             collect(DISTINCT ac {.*}) as acceptance_criteria
        RETURN g {
            .*,
            constraints: constraints,
            strategies: strategies,
            acceptance_criteria: acceptance_criteria
        } as goal
        ORDER BY g.priority ASC, g.created_at DESC
        """
        result = await self.client.execute_query(query, {"project_id": project_id})
        return [r["goal"] for r in result]

    async def get_all_goals(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all goals for a project."""
        query = """
        MATCH (g:Goal {project_id: $project_id})
        RETURN g {.*} as goal
        ORDER BY g.priority ASC, g.created_at DESC
        """
        result = await self.client.execute_query(query, {"project_id": project_id})
        return [r["goal"] for r in result]

    async def link_interaction_to_goal(
        self, interaction_id: str, goal_id: str
    ) -> None:
        """Create PRODUCED relationship between interaction and goal."""
        query = """
        MATCH (i:Interaction {id: $interaction_id})
        MATCH (g:Goal {id: $goal_id})
        MERGE (i)-[:PRODUCED]->(g)
        """
        await self.client.execute_query(
            query, {"interaction_id": interaction_id, "goal_id": goal_id}
        )

    # =========================================================================
    # Constraint Operations
    # =========================================================================

    async def upsert_constraint(
        self,
        project_id: str,
        constraint_type: str,
        description: str,
        severity: str = "must",
        goal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert a constraint node."""
        constraint_id = str(uuid4())
        query = """
        MERGE (c:Constraint {project_id: $project_id, description: $description})
        ON CREATE SET
            c.id = $constraint_id,
            c.type = $type,
            c.severity = $severity,
            c.created_at = datetime(),
            c.updated_at = datetime()
        ON MATCH SET
            c.severity = $severity,
            c.updated_at = datetime()
        RETURN c {.*} as constraint
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "constraint_id": constraint_id,
                "type": constraint_type,
                "description": description,
                "severity": severity,
            },
        )
        constraint = result[0]["constraint"] if result else {"id": constraint_id}

        # Link to goal if provided
        if goal_id:
            await self.client.execute_query(
                """
                MATCH (g:Goal {id: $goal_id})
                MATCH (c:Constraint {id: $constraint_id})
                MERGE (g)-[:HAS_CONSTRAINT]->(c)
                """,
                {"goal_id": goal_id, "constraint_id": constraint["id"]},
            )

        return constraint

    # =========================================================================
    # Preference Operations
    # =========================================================================

    async def upsert_preference(
        self,
        user_id: str,
        category: str,
        preference: str,
        strength: str = "prefer",
    ) -> Dict[str, Any]:
        """Upsert a preference node."""
        preference_id = str(uuid4())
        query = """
        MERGE (p:Preference {user_id: $user_id, category: $category, preference: $preference})
        ON CREATE SET
            p.id = $preference_id,
            p.strength = $strength,
            p.created_at = datetime(),
            p.updated_at = datetime()
        ON MATCH SET
            p.strength = $strength,
            p.updated_at = datetime()
        RETURN p {.*} as preference
        """
        result = await self.client.execute_query(
            query,
            {
                "user_id": user_id,
                "preference_id": preference_id,
                "category": category,
                "preference": preference,
                "strength": strength,
            },
        )
        return result[0]["preference"] if result else {"id": preference_id}

    async def get_preferences(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all preferences for a user."""
        query = """
        MATCH (p:Preference {user_id: $user_id})
        RETURN p {.*} as preference
        ORDER BY p.category
        """
        result = await self.client.execute_query(query, {"user_id": user_id})
        return [r["preference"] for r in result]

    # =========================================================================
    # PainPoint Operations
    # =========================================================================

    async def upsert_painpoint(
        self,
        project_id: str,
        description: str,
        severity: str = "medium",
        related_goal_id: Optional[str] = None,
        interaction_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert a pain point node."""
        painpoint_id = str(uuid4())
        query = """
        MERGE (pp:PainPoint {project_id: $project_id, description: $description})
        ON CREATE SET
            pp.id = $painpoint_id,
            pp.severity = $severity,
            pp.resolved = false,
            pp.created_at = datetime(),
            pp.updated_at = datetime()
        ON MATCH SET
            pp.severity = $severity,
            pp.updated_at = datetime()
        RETURN pp {.*} as painpoint
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "painpoint_id": painpoint_id,
                "description": description,
                "severity": severity,
            },
        )
        painpoint = result[0]["painpoint"] if result else {"id": painpoint_id}

        # Link to goal if provided
        if related_goal_id:
            await self.client.execute_query(
                """
                MATCH (g:Goal {id: $goal_id})
                MATCH (pp:PainPoint {id: $painpoint_id})
                MERGE (g)-[:BLOCKED_BY]->(pp)
                """,
                {"goal_id": related_goal_id, "painpoint_id": painpoint["id"]},
            )

        # Link to interaction if provided
        if interaction_id:
            await self.client.execute_query(
                """
                MATCH (i:Interaction {id: $interaction_id})
                MATCH (pp:PainPoint {id: $painpoint_id})
                MERGE (pp)-[:OBSERVED_IN]->(i)
                """,
                {"interaction_id": interaction_id, "painpoint_id": painpoint["id"]},
            )

        return painpoint

    async def get_open_painpoints(self, project_id: str) -> List[Dict[str, Any]]:
        """Get unresolved pain points for a project."""
        query = """
        MATCH (pp:PainPoint {project_id: $project_id, resolved: false})
        OPTIONAL MATCH (pp)<-[:BLOCKED_BY]-(g:Goal)
        WITH pp, pp.severity as severity, collect(DISTINCT g.title) as blocking_goals
        RETURN pp {
            .*,
            blocking_goals: blocking_goals
        } as painpoint
        ORDER BY 
            CASE severity 
                WHEN 'critical' THEN 1 
                WHEN 'high' THEN 2 
                WHEN 'medium' THEN 3 
                ELSE 4 
            END
        """
        result = await self.client.execute_query(query, {"project_id": project_id})
        return [r["painpoint"] for r in result]

    # =========================================================================
    # Strategy Operations
    # =========================================================================

    async def upsert_strategy(
        self,
        project_id: str,
        title: str,
        approach: str,
        rationale: Optional[str] = None,
        related_goal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert a strategy node."""
        strategy_id = str(uuid4())
        query = """
        MERGE (s:Strategy {project_id: $project_id, title: $title})
        ON CREATE SET
            s.id = $strategy_id,
            s.approach = $approach,
            s.rationale = $rationale,
            s.created_at = datetime(),
            s.updated_at = datetime()
        ON MATCH SET
            s.approach = $approach,
            s.rationale = COALESCE($rationale, s.rationale),
            s.updated_at = datetime()
        RETURN s {.*} as strategy
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "strategy_id": strategy_id,
                "title": title,
                "approach": approach,
                "rationale": rationale,
            },
        )
        strategy = result[0]["strategy"] if result else {"id": strategy_id}

        # Link to goal if provided
        if related_goal_id:
            await self.client.execute_query(
                """
                MATCH (g:Goal {id: $goal_id})
                MATCH (s:Strategy {id: $strategy_id})
                MERGE (g)-[:HAS_STRATEGY]->(s)
                """,
                {"goal_id": related_goal_id, "strategy_id": strategy["id"]},
            )

        return strategy

    # =========================================================================
    # CodeArtifact Operations
    # =========================================================================

    async def upsert_code_artifact(
        self,
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
        """Upsert a code artifact node."""
        artifact_id = str(uuid4())
        query = """
        MERGE (ca:CodeArtifact {project_id: $project_id, path: $path})
        ON CREATE SET
            ca.id = $artifact_id,
            ca.kind = $kind,
            ca.language = $language,
            ca.start_line = $start_line,
            ca.end_line = $end_line,
            ca.git_commit = $git_commit,
            ca.content_hash = $content_hash,
            ca.created_at = datetime(),
            ca.updated_at = datetime()
        ON MATCH SET
            ca.kind = $kind,
            ca.language = COALESCE($language, ca.language),
            ca.start_line = COALESCE($start_line, ca.start_line),
            ca.end_line = COALESCE($end_line, ca.end_line),
            ca.git_commit = COALESCE($git_commit, ca.git_commit),
            ca.content_hash = COALESCE($content_hash, ca.content_hash),
            ca.updated_at = datetime()
        RETURN ca {.*} as artifact
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "artifact_id": artifact_id,
                "path": path,
                "kind": kind,
                "language": language,
                "start_line": start_line,
                "end_line": end_line,
                "git_commit": git_commit,
                "content_hash": content_hash,
            },
        )
        artifact = result[0]["artifact"] if result else {"id": artifact_id, "path": path}

        # Create symbol if FQN provided
        if symbol_fqn:
            await self.upsert_symbol(artifact["id"], symbol_fqn, kind)

        # Link to goals if provided
        if related_goal_ids:
            for goal_id in related_goal_ids:
                await self.client.execute_query(
                    """
                    MATCH (g:Goal {id: $goal_id})
                    MATCH (ca:CodeArtifact {id: $artifact_id})
                    MERGE (g)-[:IMPLEMENTED_BY]->(ca)
                    """,
                    {"goal_id": goal_id, "artifact_id": artifact["id"]},
                )

        return artifact

    async def upsert_symbol(
        self,
        artifact_id: str,
        fqn: str,
        kind: str = "function",
        name: Optional[str] = None,
        line_start: Optional[int] = None,
        line_end: Optional[int] = None,
        signature: Optional[str] = None,
        change_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upsert a symbol node with full details and link to artifact.
        
        Args:
            artifact_id: ID of the parent CodeArtifact
            fqn: Fully qualified name (e.g., "src/utils.py:calculate_tax")
            kind: Symbol type: function, method, class, variable
            name: Symbol name (extracted from fqn if not provided)
            line_start: Starting line number (1-indexed)
            line_end: Ending line number (1-indexed)
            signature: Full signature (e.g., "def calculate_tax(income: float) -> float")
            change_type: What happened: added, modified, deleted, renamed
            
        Returns:
            The created/updated symbol node
        """
        symbol_id = str(uuid4())
        # Extract name from fqn if not provided
        if name is None:
            name = fqn.split(":")[-1] if ":" in fqn else fqn.split(".")[-1] if "." in fqn else fqn
        
        query = """
        MATCH (ca:CodeArtifact {id: $artifact_id})
        MERGE (s:Symbol {fqn: $fqn})
        ON CREATE SET
            s.id = $symbol_id,
            s.name = $name,
            s.kind = $kind,
            s.artifact_id = $artifact_id,
            s.line_start = $line_start,
            s.line_end = $line_end,
            s.signature = $signature,
            s.change_type = $change_type,
            s.created_at = datetime(),
            s.updated_at = datetime()
        ON MATCH SET
            s.name = $name,
            s.kind = $kind,
            s.artifact_id = $artifact_id,
            s.line_start = COALESCE($line_start, s.line_start),
            s.line_end = COALESCE($line_end, s.line_end),
            s.signature = COALESCE($signature, s.signature),
            s.change_type = $change_type,
            s.updated_at = datetime()
        MERGE (ca)-[:CONTAINS]->(s)
        RETURN s {.*} as symbol
        """
        result = await self.client.execute_query(
            query,
            {
                "artifact_id": artifact_id,
                "symbol_id": symbol_id,
                "fqn": fqn,
                "name": name,
                "kind": kind,
                "line_start": line_start,
                "line_end": line_end,
                "signature": signature,
                "change_type": change_type,
            },
        )
        return result[0]["symbol"] if result else {"id": symbol_id, "fqn": fqn}

    async def get_artifacts_for_goal(self, goal_id: str) -> List[Dict[str, Any]]:
        """Get code artifacts implementing a goal."""
        query = """
        MATCH (g:Goal {id: $goal_id})-[:IMPLEMENTED_BY]->(ca:CodeArtifact)
        OPTIONAL MATCH (ca)-[:CONTAINS]->(s:Symbol)
        WITH ca, collect(DISTINCT s {.*}) as symbols
        RETURN ca {
            .*,
            symbols: symbols
        } as artifact
        """
        result = await self.client.execute_query(query, {"goal_id": goal_id})
        return [r["artifact"] for r in result]

    # =========================================================================
    # Search Operations
    # =========================================================================

    async def fulltext_search(
        self,
        project_id: str,
        query: str,
        node_types: Optional[List[str]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Perform fulltext search across multiple node types.

        Args:
            project_id: Project to search within
            query: Search query
            node_types: Types to search (Goal, PainPoint, Strategy, etc.)
            limit: Maximum results

        Returns:
            List of matching nodes with scores
        """
        results = []

        # Search goals
        if not node_types or "Goal" in node_types:
            goal_query = """
            CALL db.index.fulltext.queryNodes('goal_fulltext', $query) YIELD node, score
            WHERE node.project_id = $project_id
            RETURN 'Goal' as type, node {.*} as data, score
            LIMIT $limit
            """
            try:
                goal_results = await self.client.execute_query(
                    goal_query, {"project_id": project_id, "query": query, "limit": limit}
                )
                results.extend(goal_results)
            except Exception as e:
                logger.warning(f"Goal fulltext search failed: {e}")

        # Search pain points
        if not node_types or "PainPoint" in node_types:
            pp_query = """
            CALL db.index.fulltext.queryNodes('painpoint_fulltext', $query) YIELD node, score
            WHERE node.project_id = $project_id
            RETURN 'PainPoint' as type, node {.*} as data, score
            LIMIT $limit
            """
            try:
                pp_results = await self.client.execute_query(
                    pp_query, {"project_id": project_id, "query": query, "limit": limit}
                )
                results.extend(pp_results)
            except Exception as e:
                logger.warning(f"PainPoint fulltext search failed: {e}")

        # Search strategies
        if not node_types or "Strategy" in node_types:
            strategy_query = """
            CALL db.index.fulltext.queryNodes('strategy_fulltext', $query) YIELD node, score
            WHERE node.project_id = $project_id
            RETURN 'Strategy' as type, node {.*} as data, score
            LIMIT $limit
            """
            try:
                strategy_results = await self.client.execute_query(
                    strategy_query, {"project_id": project_id, "query": query, "limit": limit}
                )
                results.extend(strategy_results)
            except Exception as e:
                logger.warning(f"Strategy fulltext search failed: {e}")

        # Sort by score and limit
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:limit]

    # =========================================================================
    # Impact Analysis Operations
    # =========================================================================

    async def get_impact_for_artifacts(
        self, project_id: str, paths: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze impact of changes to specified file paths.

        Returns goals, tests, and strategies that might be affected.
        """
        query = """
        MATCH (ca:CodeArtifact)
        WHERE ca.project_id = $project_id AND ca.path IN $paths
        
        // Find implementing goals
        OPTIONAL MATCH (g:Goal)-[:IMPLEMENTED_BY]->(ca)
        
        // Find related tests
        OPTIONAL MATCH (ca)-[:COVERED_BY]->(tc:TestCase)
        
        // Find strategies via goals
        OPTIONAL MATCH (g)-[:HAS_STRATEGY]->(s:Strategy)
        
        WITH 
            collect(DISTINCT g {.*}) as affected_goals,
            collect(DISTINCT tc {.*}) as tests_to_run,
            collect(DISTINCT s {.*}) as strategies_to_review,
            collect(DISTINCT ca {.*}) as artifacts
        RETURN affected_goals, tests_to_run, strategies_to_review, artifacts
        """
        result = await self.client.execute_query(
            query, {"project_id": project_id, "paths": paths}
        )

        if result:
            return {
                "goals_to_retest": [g for g in result[0]["affected_goals"] if g],
                "tests_to_run": [t for t in result[0]["tests_to_run"] if t],
                "strategies_to_review": [s for s in result[0]["strategies_to_review"] if s],
                "artifacts_related": [a for a in result[0]["artifacts"] if a],
            }
        return {
            "goals_to_retest": [],
            "tests_to_run": [],
            "strategies_to_review": [],
            "artifacts_related": [],
        }

    async def get_goal_subgraph(
        self, goal_id: str, k_hops: int = 2
    ) -> Dict[str, Any]:
        """
        Get the subgraph around a goal up to k hops.

        Returns the goal and all connected entities within k hops.
        """
        query = """
        MATCH path = (g:Goal {id: $goal_id})-[*1..$k_hops]-(connected)
        WITH g, collect(DISTINCT connected) as connected_nodes, collect(path) as paths
        RETURN g {.*} as goal, connected_nodes
        """
        result = await self.client.execute_query(
            query, {"goal_id": goal_id, "k_hops": k_hops}
        )

        if result:
            return {
                "goal": result[0]["goal"],
                "connected": result[0]["connected_nodes"],
            }
        return {"goal": None, "connected": []}


# Singleton instance
_repository: Optional[KGRepository] = None


def get_repository() -> KGRepository:
    """Get or create the repository singleton."""
    global _repository
    if _repository is None:
        _repository = KGRepository()
    return _repository
