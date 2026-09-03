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
