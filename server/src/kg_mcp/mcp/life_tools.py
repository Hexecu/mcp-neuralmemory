import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from kg_mcp.kg.repo import get_repository
from kg_mcp.utils import serialize_response

logger = logging.getLogger(__name__)


def register_life_tools(mcp: FastMCP) -> None:
    """Register Mac Life Memory tools with the MCP server."""

    @mcp.tool()
    async def capture_raw_event(
        project_id: str,
        event_type: str,
        data: Dict[str, Any],
        timestamp: Optional[str] = None,
        text_content: Optional[str] = None,
        artifact_refs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Capture a raw low-level event (e.g., focus change, browsing, keystrokes).

        Args:
            project_id: Project identifier
            event_type: Type of event ('focus', 'browse', 'input', 'system')
            data: Arbitrary JSON data associated with the event
            timestamp: ISO format timestamp (defaults to now)
            text_content: Optional textual extraction (e.g. window title, url)
            artifact_refs: List of MediaArtifact IDs (e.g. screenshot ID)
        """
        repo = get_repository()
        ts = datetime.fromisoformat(timestamp) if timestamp else datetime.now()

        try:
            result = await repo.upsert_raw_event(
                project_id=project_id,
                event_type=event_type,
                timestamp=ts,
                data=data,
                text_content=text_content,
                artifact_ids=artifact_refs,
            )
            return serialize_response(result)
        except Exception as e:
            logger.error(f"capture_raw_event failed: {e}")
            return {"error": str(e)}

    @mcp.tool()
    async def capture_activity_slice(
        project_id: str,
        start_time: str,
        end_time: str,
        summary: Optional[str] = None,
        event_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Capture an aggregated slice of user activity (e.g. 5-minute block).

        Args:
            project_id: Project identifier
            start_time: ISO format start timestamp
            end_time: ISO format end timestamp
            summary: Optional summary of what happened
            event_ids: List of RawEvent IDs included in this slice
        """
        repo = get_repository()
        t_start = datetime.fromisoformat(start_time)
        t_end = datetime.fromisoformat(end_time)

        try:
            result = await repo.upsert_activity_slice(
                project_id=project_id,
                start_time=t_start,
                end_time=t_end,
                summary=summary,
                event_ids=event_ids,
            )
            return serialize_response(result)
        except Exception as e:
            logger.error(f"capture_activity_slice failed: {e}")
            return {"error": str(e)}

    @mcp.tool()
    async def capture_meeting_session(
        project_id: str,
        title: str,
        start_time: str,
        end_time: str,
        participants: List[str],
        summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Capture a meeting session.

        Args:
            project_id: Project identifier
            title: Meeting title
            start_time: ISO format start timestamp
            end_time: ISO format end timestamp
            participants: List of participant names/emails
            summary: Optional meeting summary
        """
        repo = get_repository()
        t_start = datetime.fromisoformat(start_time)
        t_end = datetime.fromisoformat(end_time)

        try:
            result = await repo.upsert_meeting(
                project_id=project_id,
                title=title,
                start_time=t_start,
                end_time=t_end,
                participants=participants,
                summary=summary,
            )

            return serialize_response(result)
        except Exception as e:
            logger.error(f"capture_meeting_session failed: {e}")
            return {"error": str(e)}

    @mcp.tool()
    async def get_due_actions(project_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get top prioritized action items.
        """
        repo = get_repository()
        try:
            actions = await repo.get_top_actions(project_id, limit)
            return serialize_response(actions)
        except Exception as e:
            logger.error(f"get_due_actions failed: {e}")
            return [{"error": str(e)}]

    @mcp.tool()
    async def get_smart_brief(
        project_id: str,
        horizon: str = "today",
        context_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a smart context brief for the user.
        """
        repo = get_repository()
        try:
            actions = await repo.get_top_actions(project_id, limit=5)
            return {
                "brief_type": horizon,
                "summary": f"Here is your {horizon} brief based on {len(actions)} urgent items.",
                "top_actions": serialize_response(actions),
                "context_hint": context_hint,
            }
        except Exception as e:
            logger.error(f"get_smart_brief failed: {e}")
            return {"error": str(e)}

    @mcp.tool()
    async def deep_search(project_id: str, query: str, limit: int = 5) -> Dict[str, Any]:
        """
        Hybrid deep search across snippets, artifacts, episodes, and concepts.
        """
        try:
            from kg_mcp.services.deep_search import DeepSearchService

            service = DeepSearchService(project_id=project_id)
            result = await service.search(query=query, limit=limit)
            return serialize_response(result)
        except Exception as e:
            logger.error(f"deep_search failed: {e}")
            return {"error": str(e)}

    @mcp.tool()
    async def recall_decisions(
        project_id: str = "default",
        query: Optional[str] = None,
        person: Optional[str] = None,
        days_back: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Recall past decisions, approvals, confirmations, and choices.
        Answers: 'What did I approve?', 'Did I say yes to the quote?', 'Decisions with Person X'.
        """
        repo = get_repository()
        cypher = """
        MATCH (d:Decision)
        WHERE d.decided_at >= datetime() - duration({days: $days_back})
          AND ($person IS NULL OR EXISTS {
              MATCH (d)-[:TOWARDS_PERSON]->(p:Person)
              WHERE toLower(p.name) CONTAINS toLower($person)
          })
          AND ($query IS NULL OR toLower(d.title) CONTAINS toLower($query)
               OR toLower(d.rationale) CONTAINS toLower($query)
               OR toLower(d.subject) CONTAINS toLower($query))
        OPTIONAL MATCH (d)-[:TOWARDS_PERSON]->(p:Person)
        OPTIONAL MATCH (d)-[:ON_ARTIFACT]->(a:Artifact)
        OPTIONAL MATCH (d)-[:ABOUT_TOPIC]->(t:Topic)
        RETURN d.id as id, d.title as title, d.verdict as verdict, d.rationale as rationale,
               d.subject as subject, d.decided_at as decided_at,
               p.name as towards_person, a.title as artifact_title,
               collect(DISTINCT t.name) as topics
        ORDER BY decided_at DESC
        LIMIT 20
        """
        try:
            records = await repo.client.execute_query(
                cypher,
                {"days_back": days_back, "person": person, "query": query},
            )
            return serialize_response(records)
        except Exception as e:
            logger.error(f"recall_decisions failed: {e}")
            return [{"error": str(e)}]

    @mcp.tool()
    async def recall_commitments(
        project_id: str = "default",
        status: str = "open",
        person: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recall commitments, promises, and deadlines made by user or received from counterparties.
        Answers: 'What promises did I make in email/chat?', 'What pending tasks did I commit to?'.
        """
        repo = get_repository()
        cypher = """
        MATCH (c:Commitment)
        WHERE ($status = 'all' OR c.status = $status)
          AND ($person IS NULL OR EXISTS {
              MATCH (c)-[:PROMISED_TO|PROMISED_BY]->(p:Person)
              WHERE toLower(p.name) CONTAINS toLower($person)
          })
        OPTIONAL MATCH (c)-[:PROMISED_TO]->(p1:Person)
        OPTIONAL MATCH (c)-[:PROMISED_BY]->(p2:Person)
        RETURN c.id as id, c.title as title, c.task_description as task,
               c.due_date_iso as due_date, c.status as status, c.debtor as debtor,
               p1.name as creditor_name, p2.name as debtor_name, c.created_at as created_at
        ORDER BY created_at DESC
        LIMIT 25
        """
        try:
            records = await repo.client.execute_query(
                cypher,
                {"status": status, "person": person},
            )
            return serialize_response(records)
        except Exception as e:
            logger.error(f"recall_commitments failed: {e}")
            return [{"error": str(e)}]

    @mcp.tool()
    async def recall_meetings(
        project_id: str = "default",
        topic: Optional[str] = None,
        person: Optional[str] = None,
        days_back: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Recall past calls and meetings (Google Meet, Zoom, Teams, Slack Huddle).
        Answers: 'Who attended the call about pricing?', 'What calls did I have with Marco?'.
        """
        repo = get_repository()
        cypher = """
        MATCH (m:Meeting)
        WHERE m.timestamp >= datetime() - duration({days: $days_back})
          AND ($person IS NULL OR EXISTS {
              MATCH (p:Person)-[:ATTENDED]->(m)
              WHERE toLower(p.name) CONTAINS toLower($person)
          })
          AND ($topic IS NULL OR toLower(m.title) CONTAINS toLower($topic) OR EXISTS {
              MATCH (m)-[:DISCUSSED]->(t:Topic)
              WHERE toLower(t.name) CONTAINS toLower($topic)
          })
        OPTIONAL MATCH (p:Person)-[:ATTENDED]->(m)
        OPTIONAL MATCH (m)-[:DISCUSSED]->(t:Topic)
        RETURN m.id as id, m.title as title, m.duration as duration, m.timestamp as timestamp,
               collect(DISTINCT p.name) as participants,
               collect(DISTINCT t.name) as topics
        ORDER BY timestamp DESC
        LIMIT 20
        """
        try:
            records = await repo.client.execute_query(
                cypher,
                {"days_back": days_back, "person": person, "topic": topic},
            )
            return serialize_response(records)
        except Exception as e:
            logger.error(f"recall_meetings failed: {e}")
            return [{"error": str(e)}]

    @mcp.tool()
    async def get_daily_briefing(
        project_id: str = "default",
        target_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a complete executive briefing of decisions, commitments, meetings, and topics.
        """
        from kg_mcp.services.consolidator import MemoryConsolidator

        try:
            consolidator = MemoryConsolidator(project_id=project_id)
            return await consolidator.generate_daily_briefing(target_date=target_date)
        except Exception as e:
            logger.error(f"get_daily_briefing failed: {e}")
            return {"error": str(e)}

    @mcp.tool()
    async def trigger_dream_cycle(
        project_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Trigger a subconscious Dream Consolidation cycle across the Knowledge Graph.
        Replays recent events, identifies emergent strategic themes, and synthesizes Reflections.
        """
        from kg_mcp.services.consolidator import MemoryConsolidator

        try:
            consolidator = MemoryConsolidator(project_id=project_id)
            return await consolidator.run_dream_cycle()
        except Exception as e:
            logger.error(f"trigger_dream_cycle failed: {e}")
            return {"error": str(e)}

    @mcp.tool()
    async def recall_reflections(
        project_id: str = "default",
        category: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Recall higher-order strategic reflections and emergent patterns generated in Dream Mode.
        Answers: 'What strategic patterns emerged recently?', 'What does Dream Mode say about X?'.
        """
        from kg_mcp.services.consolidator import MemoryConsolidator

        try:
            consolidator = MemoryConsolidator(project_id=project_id)
            return await consolidator.recall_reflections(
                category=category, topic=topic, limit=limit
            )
        except Exception as e:
            logger.error(f"recall_reflections failed: {e}")
            return [{"error": str(e)}]
