"""
SliceBuilder - Builds ActivitySlices from RawEvents

Temporal chunking: groups raw events into 5-minute slices with semantic summaries.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import uuid4

from kg_mcp.kg.repo import get_repository

logger = logging.getLogger(__name__)


class SliceBuilder:
    """
    Builds ActivitySlices from RawEvents using temporal chunking.

    Each slice represents a coherent block of user activity (default: 5 min).
    """

    SLICE_DURATION_MINUTES = 5

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.repo = get_repository()

    async def build_slices_from_events(
        self,
        events: List[Dict[str, Any]],
        duration_minutes: int = SLICE_DURATION_MINUTES
    ) -> List[Dict[str, Any]]:
        """
        Group events into temporal slices.

        Args:
            events: List of RawEvent dicts with 'id', 'timestamp', 'text_content', etc.
            duration_minutes: Duration of each slice in minutes

        Returns:
            List of ActivitySlice dicts ready for upsert
        """
        if not events:
            return []

        # Sort by timestamp
        sorted_events = sorted(
            events,
            key=lambda e: self._parse_timestamp(e.get("timestamp"))
        )

        slices = []
        current_slice_events = []
        slice_start = None

        for event in sorted_events:
            event_ts = self._parse_timestamp(event.get("timestamp"))

            if slice_start is None:
                slice_start = event_ts

            # Check if event is beyond current slice window
            if event_ts > slice_start + timedelta(minutes=duration_minutes):
                # Finalize current slice
                if current_slice_events:
                    slice_data = self._create_slice(
                        current_slice_events,
                        slice_start,
                        slice_start + timedelta(minutes=duration_minutes)
                    )
                    slices.append(slice_data)

                # Start new slice
                slice_start = event_ts
                current_slice_events = [event]
            else:
                current_slice_events.append(event)

        # Finalize last slice
        if current_slice_events:
            slice_end = self._parse_timestamp(current_slice_events[-1].get("timestamp"))
            slice_data = self._create_slice(
                current_slice_events,
                slice_start,
                slice_end
            )
            slices.append(slice_data)

        return slices

    def _create_slice(
        self,
        events: List[Dict[str, Any]],
        start: datetime,
        end: datetime
    ) -> Dict[str, Any]:
        """Create an ActivitySlice dict from events."""

        # Extract unique apps and windows
        apps = set()
        windows = set()
        has_keystroke = False
        has_screenshot = False

        for e in events:
            data = e.get("data", {})
            if isinstance(data, str):
                import json
                try:
                    data = json.loads(data)
                except:
                    data = {}

            if data.get("app"):
                apps.add(data.get("app"))
            if data.get("window"):
                windows.add(data.get("window"))
            if e.get("type") == "keystroke_buffer":
                has_keystroke = True
            if data.get("has_screenshot"):
                has_screenshot = True

        # Build summary
        summary_parts = []
        if apps:
            summary_parts.append(f"Apps: {', '.join(list(apps)[:5])}")
        if has_keystroke:
            summary_parts.append("Typing activity")
        if has_screenshot:
            summary_parts.append("Screenshots captured")

        summary = "; ".join(summary_parts) if summary_parts else "Activity recorded"

        return {
            "id": str(uuid4()),
            "project_id": self.project_id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "summary": summary,
            "event_count": len(events),
            "event_ids": [e.get("id") for e in events],
            "apps": list(apps),
            "has_keystroke": has_keystroke,
            "has_screenshot": has_screenshot,
            "confidence": 0.8,  # Default confidence
        }

    async def upsert_slice(self, slice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save ActivitySlice to Neo4j and link to its events.
        """
        query = """
        MATCH (p:Project {id: $project_id})
        CREATE (s:ActivitySlice {
            id: $id,
            project_id: $project_id,
            start_time: datetime($start_time),
            end_time: datetime($end_time),
            summary: $summary,
            event_count: $event_count,
            apps: $apps,
            has_keystroke: $has_keystroke,
            has_screenshot: $has_screenshot,
            confidence: $confidence,
            created_at: datetime()
        })
        MERGE (s)-[:IN_PROJECT]->(p)

        WITH s
        UNWIND $apps as app_name
        MERGE (a:App {name: app_name})
        ON CREATE SET a.id = randomUUID(), a.created_at = datetime()
        MERGE (s)-[:USED_APP]->(a)

        RETURN s {.*} as slice
        """

        result = await self.repo.client.execute_query(
            query,
            {
                "id": slice_data["id"],
                "project_id": slice_data["project_id"],
                "start_time": slice_data["start_time"],
                "end_time": slice_data["end_time"],
                "summary": slice_data["summary"],
                "event_count": slice_data["event_count"],
                "apps": slice_data["apps"],
                "has_keystroke": slice_data["has_keystroke"],
                "has_screenshot": slice_data["has_screenshot"],
                "confidence": slice_data["confidence"],
            }
        )

        # Link events to slice
        if slice_data.get("event_ids"):
            link_query = """
            MATCH (s:ActivitySlice {id: $slice_id})
            MATCH (e:RawEvent) WHERE e.id IN $event_ids
            MERGE (e)-[:IN_SLICE]->(s)
            """
            await self.repo.client.execute_query(
                link_query,
                {
                    "slice_id": slice_data["id"],
                    "event_ids": slice_data["event_ids"],
                }
            )

        logger.info(f"Created ActivitySlice {slice_data['id']} with {slice_data['event_count']} events")
        return slice_data

    def _parse_timestamp(self, ts: Any) -> datetime:
        """Parse timestamp from various formats."""
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            # Handle ISO format
            ts = ts.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(ts)
            except:
                pass
        return datetime.now()
