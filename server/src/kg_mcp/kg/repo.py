"""
Repository layer for Neo4j queries.
Provides typed query functions for CRUD operations on the knowledge graph.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from kg_mcp.kg.client import get_neo4j_client

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
        if self.client.use_embedded:
            return self.client.sqlite_store.get_or_create_project(project_id, name)

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
        outcome: Optional[str] = None,
        outcome_reason: Optional[str] = None,
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
            s.outcome = $outcome,
            s.outcome_reason = $outcome_reason,
            s.created_at = datetime(),
            s.updated_at = datetime()
        ON MATCH SET
            s.approach = $approach,
            s.rationale = COALESCE($rationale, s.rationale),
            s.outcome = COALESCE($outcome, s.outcome),
            s.outcome_reason = COALESCE($outcome_reason, s.outcome_reason),
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
                "outcome": outcome,
                "outcome_reason": outcome_reason,
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
    # Mac Life Memory Operations
    # =========================================================================

    async def upsert_raw_event(
        self,
        project_id: str,
        event_type: str,
        timestamp: datetime,
        data: Dict[str, Any],
        text_content: Optional[str] = None,
        artifact_ids: Optional[List[str]] = None,
        normalized_event_type: Optional[str] = None,
        screenshot_hash: Optional[str] = None,
        artifact_canonical_id: Optional[str] = None,
        app: Optional[str] = None,
        window_title: Optional[str] = None,
        url_or_path: Optional[str] = None,
        is_duplicate: Optional[bool] = None,
        duplicate_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert a raw event node."""
        if self.client.use_embedded:
            res = self.client.sqlite_store.upsert_raw_event(
                project_id=project_id,
                event_type=event_type,
                timestamp=timestamp,
                data=data,
                text_content=text_content,
                screenshot_hash=screenshot_hash,
                is_duplicate=is_duplicate,
                duplicate_of=duplicate_of,
            )
            return {"event": res, **res}

        event_id = str(uuid4())
        # Ensure timestamp is ISO formatted string for Neo4j if passing as string,
        # but the driver handles datetime objects well in parameters usually.
        # However, for consistency we might want to ensure it is passed correctly.

        query = """
        MERGE (p:Project {id: $project_id})
        ON CREATE SET p.name = $project_id, p.created_at = datetime()
        CREATE (re:RawEvent {
            id: $event_id,
            type: $event_type,
            normalized_type: $normalized_event_type,
            timestamp: $timestamp,
            data: $data_json,
            text_content: $text_content,
            project_id: $project_id,
            app: $app,
            window_title: $window_title,
            url_or_path: $url_or_path,
            artifact_canonical_id: $artifact_canonical_id,
            screenshot_hash: $screenshot_hash,
            is_duplicate: $is_duplicate,
            duplicate_of: $duplicate_of,
            created_at: datetime()
        })
        MERGE (re)-[:IN_PROJECT]->(p)
        RETURN re {.*} as event
        """

        # Serialize data to JSON string for storage if it's a dict
        import json
        data_json = json.dumps(data)

        # Best-effort extraction of common fields from data
        if isinstance(data, dict):
            if app is None:
                app = data.get("app")
            if window_title is None:
                window_title = data.get("window") or data.get("window_title")
            if url_or_path is None:
                url_or_path = data.get("url") or data.get("url_or_path") or data.get("path")
            if artifact_canonical_id is None:
                artifact_canonical_id = data.get("artifact_canonical_id")

        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "event_id": event_id,
                "event_type": event_type,
                "normalized_event_type": normalized_event_type,
                "timestamp": timestamp,
                "data_json": data_json,
                "text_content": text_content,
                "app": app,
                "window_title": window_title,
                "url_or_path": url_or_path,
                "artifact_canonical_id": artifact_canonical_id,
                "screenshot_hash": screenshot_hash,
                "is_duplicate": is_duplicate,
                "duplicate_of": duplicate_of,
            },
        )
        event = result[0]["event"] if result else {"id": event_id}

        # Link artifacts
        if artifact_ids:
            for art_id in artifact_ids:
                await self.client.execute_query(
                    """
                    MATCH (re:RawEvent {id: $event_id})
                    MATCH (ma:MediaArtifact {id: $art_id})
                    MERGE (re)-[:HAS_ARTIFACT]->(ma)
                    """,
                    {"event_id": event["id"], "art_id": art_id},
                )

        return event

    async def upsert_media_artifact(
        self,
        project_id: str,
        uri: str,
        kind: str,
        content_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert a media artifact (screenshot/audio)."""
        artifact_id = str(uuid4())
        query = """
        MATCH (p:Project {id: $project_id})
        MERGE (ma:MediaArtifact {uri: $uri})
        ON CREATE SET
            ma.id = $artifact_id,
            ma.project_id = $project_id,
            ma.kind = $kind,
            ma.content_hash = $content_hash,
            ma.created_at: datetime()
        ON MATCH SET
            ma.updated_at = datetime()
        MERGE (ma)-[:IN_PROJECT]->(p)
        RETURN ma {.*} as artifact
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "artifact_id": artifact_id,
                "uri": uri,
                "kind": kind,
                "content_hash": content_hash,
            }
        )
        return result[0]["artifact"] if result else {"id": artifact_id}

    async def upsert_activity_slice(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime,
        summary: Optional[str] = None,
        event_ids: Optional[List[str]] = None,
        apps: Optional[List[str]] = None,
        artifact_ids: Optional[List[str]] = None,
        concept_names: Optional[List[str]] = None,
        event_types: Optional[List[str]] = None,
        primary_app: Optional[str] = None,
        primary_artifact_id: Optional[str] = None,
        primary_concept: Optional[str] = None,
        duplicate_count: int = 0,
        confidence: float = 0.8,
        segment_kind: str = "semantic",
    ) -> Dict[str, Any]:
        """Upsert an activity slice."""
        if self.client.use_embedded:
            res = self.client.sqlite_store.upsert_activity_slice(
                project_id=project_id,
                start_time=start_time,
                end_time=end_time,
                summary=summary,
                event_ids=event_ids,
            )
            return {"slice": res, **res}

        slice_id = str(uuid4())
        query = """
        MATCH (p:Project {id: $project_id})
        CREATE (as:ActivitySlice {
            id: $slice_id,
            start_time: $start_time,
            end_time: $end_time,
            summary: $summary,
            project_id: $project_id,
            apps: $apps,
            concepts: $concepts,
            artifact_ids: $artifact_ids,
            event_types: $event_types,
            primary_app: $primary_app,
            primary_artifact_id: $primary_artifact_id,
            primary_concept: $primary_concept,
            duplicate_count: $duplicate_count,
            confidence: $confidence,
            segment_kind: $segment_kind,
            created_at: datetime()
        })
        MERGE (as)-[:IN_PROJECT]->(p)
        RETURN as {.*} as slice
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "slice_id": slice_id,
                "start_time": start_time,
                "end_time": end_time,
                "summary": summary,
                "apps": apps or [],
                "concepts": concept_names or [],
                "artifact_ids": artifact_ids or [],
                "event_types": event_types or [],
                "primary_app": primary_app,
                "primary_artifact_id": primary_artifact_id,
                "primary_concept": primary_concept,
                "duplicate_count": duplicate_count,
                "confidence": confidence,
                "segment_kind": segment_kind,
            }
        )
        slice_node = result[0]["slice"] if result else {"id": slice_id}

        if event_ids:
            # Link events to slice using IN_SLICE (Event -> Slice)
             await self.client.execute_query(
                """
                MATCH (as:ActivitySlice {id: $slice_id})
                MATCH (re:RawEvent) WHERE re.id IN $event_ids
                MERGE (re)-[:IN_SLICE]->(as)
                """,
                {"slice_id": slice_node["id"], "event_ids": event_ids}
            )

        if apps:
            await self.client.execute_query(
                """
                MATCH (s:ActivitySlice {id: $slice_id})
                UNWIND $apps as app_name
                MERGE (a:App {name: app_name})
                ON CREATE SET a.id = randomUUID(), a.created_at = datetime()
                MERGE (s)-[:USED_APP]->(a)
                """,
                {"slice_id": slice_node["id"], "apps": apps}
            )

        if artifact_ids:
            await self.client.execute_query(
                """
                MATCH (s:ActivitySlice {id: $slice_id})
                UNWIND $artifact_ids as art_id
                MATCH (a:Artifact {id: art_id})
                MERGE (s)-[:USED_ARTIFACT]->(a)
                """,
                {"slice_id": slice_node["id"], "artifact_ids": artifact_ids}
            )

        if concept_names:
            await self.client.execute_query(
                """
                MATCH (p:Project {id: $project_id})
                MATCH (s:ActivitySlice {id: $slice_id})
                UNWIND $concept_names as cname
                MERGE (t:Topic:Concept {name: cname})
                ON CREATE SET t.id = randomUUID(), t.created_at = datetime(), t.project_id = $project_id
                MERGE (t)-[:IN_PROJECT]->(p)
                MERGE (s)-[:ABOUT]->(t)
                """,
                {"project_id": project_id, "slice_id": slice_node["id"], "concept_names": concept_names}
            )

        return slice_node

    async def upsert_activity_session(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime,
        title: str,
        summary: Optional[str] = None,
        outcome: Optional[str] = None,
        concepts: Optional[List[str]] = None,
        artifact_ids: Optional[List[str]] = None,
        duration_seconds: Optional[int] = None,
        open_loops: Optional[List[str]] = None,
        confidence: float = 0.8,
        embedding: Optional[List[float]] = None,
        primary_concept: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert an activity session (episode)."""
        session_id = str(uuid4())
        query = """
        MATCH (p:Project {id: $project_id})
        CREATE (s:ActivitySession {
            id: $session_id,
            project_id: $project_id,
            title: $title,
            summary: $summary,
            outcome: $outcome,
            concepts: $concepts,
            artifact_ids: $artifact_ids,
            topic_name: $primary_concept,
            duration_seconds: $duration_seconds,
            open_loops: $open_loops,
            confidence: $confidence,
            start_time: $start_time,
            end_time: $end_time,
            embedding: $embedding,
            created_at: datetime()
        })
        MERGE (s)-[:IN_PROJECT]->(p)
        RETURN s {.*} as session
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "session_id": session_id,
                "title": title,
                "summary": summary,
                "outcome": outcome,
                "concepts": concepts or [],
                "artifact_ids": artifact_ids or [],
                "primary_concept": primary_concept,
                "duration_seconds": duration_seconds,
                "open_loops": open_loops or [],
                "confidence": confidence,
                "start_time": start_time,
                "end_time": end_time,
                "embedding": embedding,
            }
        )
        return result[0]["session"] if result else {"id": session_id}

    async def link_slice_to_session(self, slice_id: str, session_id: str) -> None:
        """Link an ActivitySlice to an ActivitySession."""
        await self.client.execute_query(
            """
            MATCH (s:ActivitySlice {id: $slice_id})
            MATCH (ep:ActivitySession {id: $session_id})
            MERGE (s)-[:IN_SESSION]->(ep)
            """,
            {"slice_id": slice_id, "session_id": session_id}
        )

    async def upsert_artifact(
        self,
        project_id: str,
        canonical_id: str,
        artifact_type: str = "unknown",
        title: Optional[str] = None,
        url_or_path: Optional[str] = None,
        owner_org: Optional[str] = None,
        embedding: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Upsert a general artifact node (doc/email/web/ticket/etc)."""
        artifact_id = str(uuid4())
        query = """
        MATCH (p:Project {id: $project_id})
        MERGE (a:Artifact {canonical_id: $canonical_id})
        ON CREATE SET
            a.id = $artifact_id,
            a.project_id = $project_id,
            a.type = $artifact_type,
            a.title = $title,
            a.url_or_path = $url_or_path,
            a.owner_org = $owner_org,
            a.embedding = $embedding,
            a.created_at = datetime(),
            a.last_seen_at = datetime()
        ON MATCH SET
            a.type = COALESCE($artifact_type, a.type),
            a.title = COALESCE($title, a.title),
            a.url_or_path = COALESCE($url_or_path, a.url_or_path),
            a.owner_org = COALESCE($owner_org, a.owner_org),
            a.embedding = COALESCE($embedding, a.embedding),
            a.last_seen_at = datetime()
        MERGE (a)-[:IN_PROJECT]->(p)
        RETURN a {.*} as artifact
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "canonical_id": canonical_id,
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "title": title,
                "url_or_path": url_or_path,
                "owner_org": owner_org,
                "embedding": embedding,
            }
        )
        return result[0]["artifact"] if result else {"id": artifact_id, "canonical_id": canonical_id}

    async def link_event_to_artifact(self, event_id: str, artifact_id: str) -> None:
        """Link a RawEvent to an Artifact."""
        await self.client.execute_query(
            """
            MATCH (re:RawEvent {id: $event_id})
            MATCH (a:Artifact {id: $artifact_id})
            MERGE (re)-[:ON]->(a)
            """,
            {"event_id": event_id, "artifact_id": artifact_id}
        )

    async def link_event_to_app(self, event_id: str, app_name: str) -> None:
        """Link a RawEvent to a Source App."""
        if not app_name:
            return
        await self.client.execute_query(
            """
            MATCH (re:RawEvent {id: $event_id})
            MERGE (a:App {name: $app_name})
            ON CREATE SET a.id = randomUUID(), a.created_at = datetime()
            MERGE (re)-[:USED_APP]->(a)
            """,
            {"event_id": event_id, "app_name": app_name}
        )

    async def link_event_to_topic(
        self,
        event_id: str,
        topic_name: str,
        confidence: float = 0.8,
    ) -> None:
        """Link a RawEvent to a Topic (Concept)."""
        if not topic_name:
            return
        await self.client.execute_query(
            """
            MATCH (re:RawEvent {id: $event_id})
            MATCH (p:Project {id: re.project_id})
            MERGE (t:Topic:Concept {name: $topic_name})
            ON CREATE SET t.id = randomUUID(), t.created_at = datetime(), t.frequency_7d = 1, t.last_seen_at = datetime(), t.project_id = re.project_id
            ON MATCH SET t.last_seen_at = datetime(), t.frequency_7d = COALESCE(t.frequency_7d, 0) + 1
            MERGE (t)-[:IN_PROJECT]->(p)
            MERGE (re)-[m:MENTIONED]->(t)
            ON CREATE SET m.confidence = $confidence, m.created_at = datetime()
            ON MATCH SET m.confidence = CASE WHEN $confidence > m.confidence THEN $confidence ELSE m.confidence END
            """,
            {"event_id": event_id, "topic_name": topic_name, "confidence": confidence}
        )

    async def upsert_snippet(
        self,
        project_id: str,
        text: str,
        confidence: float = 0.6,
        embedding: Optional[List[float]] = None,
        source_event_id: Optional[str] = None,
        artifact_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a snippet node and link to event/artifact if provided."""
        snippet_id = str(uuid4())
        query = """
        MATCH (p:Project {id: $project_id})
        CREATE (s:Snippet {
            id: $snippet_id,
            project_id: $project_id,
            text: $text,
            confidence: $confidence,
            embedding: $embedding,
            created_at: datetime()
        })
        MERGE (s)-[:IN_PROJECT]->(p)
        RETURN s {.*} as snippet
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "snippet_id": snippet_id,
                "text": text,
                "confidence": confidence,
                "embedding": embedding,
            }
        )
        snippet = result[0]["snippet"] if result else {"id": snippet_id}

        if source_event_id:
            await self.client.execute_query(
                """
                MATCH (s:Snippet {id: $snippet_id})
                MATCH (re:RawEvent {id: $event_id})
                MERGE (s)-[:FROM_EVENT]->(re)
                """,
                {"snippet_id": snippet["id"], "event_id": source_event_id}
            )

        if artifact_id:
            await self.client.execute_query(
                """
                MATCH (s:Snippet {id: $snippet_id})
                MATCH (a:Artifact {id: $artifact_id})
                MERGE (s)-[:ABOUT]->(a)
                """,
                {"snippet_id": snippet["id"], "artifact_id": artifact_id}
            )

        return snippet

    async def upsert_concept_relation(
        self,
        concept_a: str,
        concept_b: str,
        weight: float = 1.0,
    ) -> None:
        """Upsert co-occurrence relation between concepts."""
        if not concept_a or not concept_b or concept_a == concept_b:
            return
        await self.client.execute_query(
            """
            MERGE (a:Topic:Concept {name: $concept_a})
            MERGE (b:Topic:Concept {name: $concept_b})
            MERGE (a)-[r:RELATED]->(b)
            ON CREATE SET r.weight = $weight, r.updated_at = datetime()
            ON MATCH SET r.weight = COALESCE(r.weight, 0) + $weight, r.updated_at = datetime()
            """,
            {"concept_a": concept_a, "concept_b": concept_b, "weight": weight}
        )

    async def get_last_screenshot_event(
        self,
        project_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Fetch the most recent RawEvent with a screenshot hash."""
        if self.client.use_embedded:
            return self.client.sqlite_store.get_last_screenshot_event(project_id)

        query = """
        MATCH (re:RawEvent {project_id: $project_id})
        WHERE re.screenshot_hash IS NOT NULL AND (re.is_duplicate IS NULL OR re.is_duplicate = false)
        RETURN re {.*, id: re.id} as event
        ORDER BY re.timestamp DESC
        LIMIT 1
        """
        result = await self.client.execute_query(query, {"project_id": project_id})
        if result:
            return result[0]["event"]
        return None

    async def upsert_meeting(
        self,
        project_id: str,
        title: str,
        start_time: datetime,
        end_time: datetime,
        participants: List[str],
        summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert a meeting."""
        meeting_id = str(uuid4())
        query = """
        MATCH (p:Project {id: $project_id})
        CREATE (m:Meeting {
            id: $meeting_id,
            title: $title,
            start_time: $start_time,
            end_time: $end_time,
            summary: $summary,
            project_id: $project_id,
            created_at: datetime()
        })
        MERGE (m)-[:IN_PROJECT]->(p)
        RETURN m {.*} as meeting
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "meeting_id": meeting_id,
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "summary": summary,
            }
        )
        meeting = result[0]["meeting"] if result else {"id": meeting_id}

        # Link participants
        for person_name in participants:
            await self.client.execute_query(
                """
                MATCH (m:Meeting {id: $meeting_id})
                MERGE (p:Person {name: $name})
                MERGE (m)-[:PARTICIPANT]->(p)
                """,
                {"meeting_id": meeting["id"], "name": person_name}
            )
        return meeting

    async def upsert_action_item(
        self,
        project_id: str,
        title: str,
        status: str = "open",
        due_at: Optional[datetime] = None,
        priority: str = "medium",
        score: float = 0.0,
        source_id: Optional[str] = None, # Slice ID or Meeting ID
        assigned_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert an action item."""
        action_id = str(uuid4())
        query = """
        MATCH (p:Project {id: $project_id})
        MERGE (ai:ActionItem {project_id: $project_id, title: $title})
        ON CREATE SET
            ai.id = $action_id,
            ai.status = $status,
            ai.due_at = $due_at,
            ai.priority = $priority,
            ai.score = $score,
            ai.created_at = datetime(),
            ai.updated_at = datetime()
        ON MATCH SET
            ai.status = $status,
            ai.due_at = COALESCE($due_at, ai.due_at),
            ai.priority = $priority,
            ai.score = $score,
            ai.updated_at = datetime()
        MERGE (ai)-[:RELATED_TO]->(p)
        RETURN ai {.*} as action
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "action_id": action_id,
                "title": title,
                "status": status,
                "due_at": due_at,
                "priority": priority,
                "score": score,
            }
        )
        action = result[0]["action"] if result else {"id": action_id}

        # Source link
        if source_id:
             await self.client.execute_query(
                """
                MATCH (ai:ActionItem {id: $action_id})
                MATCH (source) WHERE source.id = $source_id
                MERGE (ai)-[:DERIVED_FROM]->(source)
                """,
                {"action_id": action["id"], "source_id": source_id}
            )

        # Assignee link
        if assigned_to:
             await self.client.execute_query(
                """
                MATCH (ai:ActionItem {id: $action_id})
                MERGE (p:Person {name: $name})
                MERGE (ai)-[:ASSIGNED_TO]->(p)
                """,
                {"action_id": action["id"], "name": assigned_to}
            )

        return action

    async def get_top_actions(
        self,
        project_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get top action items sorted by urgency score."""
        query = """
        MATCH (ai:ActionItem {project_id: $project_id})
        WHERE ai.status <> 'completed'
        RETURN ai {.*} as action
        ORDER BY ai.score DESC, ai.due_at ASC
        LIMIT $limit
        """
        result = await self.client.execute_query(query, {"project_id": project_id, "limit": limit})
        return [r["action"] for r in result]

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

    # =========================================================================
    # Knowledge Graph Refinement Operations (Gardener)
    # =========================================================================

    async def upsert_topic(
        self,
        project_id: str,
        name: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upsert a Topic node."""
        topic_id = str(uuid4())
        query = """
        MATCH (p:Project {id: $project_id})
        MERGE (t:Topic:Concept {project_id: $project_id, name: $name})
        ON CREATE SET
            t.id = $topic_id,
            t.description = $description,
            t.created_at = datetime(),
            t.updated_at = datetime()
        ON MATCH SET
            t.description = COALESCE($description, t.description),
            t.updated_at = datetime()
        MERGE (t)-[:IN_PROJECT]->(p)
        RETURN t {.*} as topic
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "topic_id": topic_id,
                "name": name,
                "description": description,
            }
        )
        return result[0]["topic"] if result else {"id": topic_id, "name": name}

    async def upsert_fact(
        self,
        project_id: str,
        content: str,
        topic_name: Optional[str] = None,
        source_id: Optional[str] = None,  # ActivitySession ID
        valid_from: Optional[datetime] = None,
        confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """Upsert a Fact node."""
        fact_id = str(uuid4())
        query = """
        MATCH (p:Project {id: $project_id})
        CREATE (f:Fact {
            id: $fact_id,
            content: $content,
            project_id: $project_id,
            confidence: $confidence,
            valid_from: $valid_from,
            created_at: datetime()
        })
        MERGE (f)-[:IN_PROJECT]->(p)
        RETURN f {.*} as fact
        """
        result = await self.client.execute_query(
            query,
            {
                "project_id": project_id,
                "fact_id": fact_id,
                "content": content,
                "confidence": confidence,
                "valid_from": valid_from or datetime.now(),
            }
        )
        fact = result[0]["fact"] if result else {"id": fact_id}

        # Link to Topic
        if topic_name:
            # Ensure topic exists first
            await self.upsert_topic(project_id, topic_name)
            await self.client.execute_query(
                """
                MATCH (f:Fact {id: $fact_id})
                MATCH (t:Topic:Concept {project_id: $project_id, name: $topic_name})
                MERGE (t)-[:HAS_FACT]->(f)
                """,
                {"fact_id": fact["id"], "project_id": project_id, "topic_name": topic_name}
            )

        # Link to Source Session
        if source_id:
            await self.client.execute_query(
                """
                MATCH (f:Fact {id: $fact_id})
                MATCH (s:ActivitySession {id: $source_id})
                MERGE (s)-[:REVEALED]->(f)
                """,
                {"fact_id": fact["id"], "source_id": source_id}
            )

        return fact



    async def upsert_entity(
        self,
        project_id: str,
        name: str,
        entity_type: str,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upsert a generic entity (Person, App, Organization)."""
        if entity_type not in ["Person", "App", "Organization"]:
            raise ValueError(f"Unsupported entity type: {entity_type}")

        if not name:
             return {}

        query = f"""
        MATCH (p:Project {{id: $project_id}})
        MERGE (e:{entity_type} {{name: $name}})
        ON CREATE SET e.created_at = datetime(), e.updated_at = datetime()
        ON MATCH SET e.updated_at = datetime()

        // Link to project (affiliation context)
        MERGE (e)-[:ASSOCIATED_WITH]->(p)
        RETURN e {{.*}} as entity
        """

        result = await self.client.execute_query(
            query,
            {"project_id": project_id, "name": name}
        )
        return result[0]["entity"] if result else {}



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


    async def upsert_research_brief(
        self,
        project_id: str,
        topic_name: str,
        content: str,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upsert a Research Brief node."""
        brief_id = str(uuid4())

        query = """
        MATCH (p:Project {id: $project_id})
        MERGE (t:Topic:Concept {name: $topic_name})
        ON CREATE SET t.id = $topic_id, t.created_at = datetime(), t.project_id = $project_id
        MERGE (t)-[:IN_PROJECT]->(p)

        CREATE (rb:ResearchBrief {
            id: $brief_id,
            content: $content,
            url: $url,
            created_at: datetime()
        })

        MERGE (rb)-[:ABOUT_TOPIC]->(t)
        MERGE (rb)-[:IN_PROJECT]->(p)
        RETURN rb {.*} as brief
        """

        params = {
            "project_id": project_id,
            "brief_id": brief_id,
            "topic_id": str(uuid4()),
            "topic_name": topic_name,
            "content": content,
            "url": url
        }

        result = await self.client.execute_query(query, params)
        return result[0]["brief"] if result else {}

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
