"""
Sessionizer - Groups semantic segments into higher-level episodes (ActivitySessions).
"""
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from kg_mcp.config import get_settings
from kg_mcp.kg.repo import get_repository

logger = logging.getLogger(__name__)


class Sessionizer:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.repo = get_repository()
        self.settings = get_settings()

    async def build_sessions_from_segments(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not segments:
            return []

        sorted_segments = sorted(segments, key=lambda s: self._parse_timestamp(s.get("start_time")))
        sessions: List[Dict[str, Any]] = []
        current: Dict[str, Any] = {}

        for segment in sorted_segments:
            seg_start = self._parse_timestamp(segment.get("start_time"))
            if not current:
                current = self._init_session(segment, seg_start)
                continue

            if self._should_break(current, segment, seg_start):
                sessions.append(await self._finalize_session(current))
                current = self._init_session(segment, seg_start)
            else:
                self._append_segment(current, segment)

        if current:
            sessions.append(await self._finalize_session(current))

        return sessions

    def _init_session(self, segment: Dict[str, Any], seg_start: datetime) -> Dict[str, Any]:
        concepts = segment.get("concepts") or []
        artifacts = segment.get("artifact_ids") or []
        event_types = segment.get("event_types") or []
        open_loops = []
        if "TODO_FOUND" in event_types or "ERROR_BLOCKER" in event_types:
            open_loops.append(segment.get("summary"))

        return {
            "segment_ids": [segment.get("id")],
            "start_time": seg_start,
            "end_time": self._parse_timestamp(segment.get("end_time")),
            "concepts": Counter(concepts),
            "artifact_ids": Counter(artifacts),
            "apps": set(segment.get("apps") or []),
            "event_types": set(event_types),
            "open_loops": [l for l in open_loops if l],
            "summaries": [segment.get("summary")] if segment.get("summary") else [],
        }

    def _append_segment(self, session: Dict[str, Any], segment: Dict[str, Any]) -> None:
        session["segment_ids"].append(segment.get("id"))
        session["end_time"] = self._parse_timestamp(segment.get("end_time"))
        for concept in segment.get("concepts") or []:
            session["concepts"][concept] += 1
        for artifact_id in segment.get("artifact_ids") or []:
            session["artifact_ids"][artifact_id] += 1
        for app in segment.get("apps") or []:
            session["apps"].add(app)
        for event_type in segment.get("event_types") or []:
            session["event_types"].add(event_type)
        if segment.get("summary"):
            session["summaries"].append(segment.get("summary"))
        if "TODO_FOUND" in (segment.get("event_types") or []) or "ERROR_BLOCKER" in (segment.get("event_types") or []):
            if segment.get("summary"):
                session["open_loops"].append(segment.get("summary"))

    def _should_break(self, session: Dict[str, Any], segment: Dict[str, Any], seg_start: datetime) -> bool:
        gap = seg_start - session["end_time"]
        if gap > timedelta(minutes=self.settings.session_gap_minutes):
            return True

        event_types = set(segment.get("event_types") or [])
        if "MEETING" in event_types or "CONTEXT_SWITCH" in event_types:
            return True

        similarity = self._concept_similarity(
            set(session["concepts"].keys()),
            set(segment.get("concepts") or []),
        )
        if similarity < 0.2 and gap > timedelta(minutes=2):
            return True

        apps = set(segment.get("apps") or [])
        if apps and session["apps"] and not (apps & session["apps"]) and similarity < 0.2:
            return True

        return False

    async def _finalize_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        concepts = [c for c, _ in session["concepts"].most_common(5)]
        artifacts = [a for a, _ in session["artifact_ids"].most_common(5)]
        title = await self._build_title(artifacts, concepts, session["apps"])
        summary = self._build_summary(session["summaries"], concepts)
        duration = int((session["end_time"] - session["start_time"]).total_seconds())

        return {
            "project_id": self.project_id,
            "start_time": session["start_time"].isoformat(),
            "end_time": session["end_time"].isoformat(),
            "title": title,
            "summary": summary,
            "concepts": concepts,
            "artifact_ids": artifacts,
            "duration_seconds": duration,
            "open_loops": session["open_loops"],
            "segment_ids": session["segment_ids"],
            "confidence": 0.8,
        }

    async def _build_title(self, artifact_ids: List[str], concepts: List[str], apps: set) -> str:
        artifact_title = await self._resolve_artifact_title(artifact_ids)
        if artifact_title:
            return f"Working on {artifact_title}"
        if concepts:
            return f"Working on {concepts[0]}"
        if apps:
            return f"Work in {list(apps)[0]}"
        return "Activity Session"

    def _build_summary(self, summaries: List[str], concepts: List[str]) -> str:
        if summaries:
            return "; ".join(summaries[:5])
        if concepts:
            return "Focus: " + ", ".join(concepts[:3])
        return "Activity session"

    async def _resolve_artifact_title(self, artifact_ids: List[str]) -> Optional[str]:
        if not artifact_ids:
            return None
        artifact_key = artifact_ids[0]
        query = """
        MATCH (a:Artifact)
        WHERE a.id = $artifact_key OR a.canonical_id = $artifact_key
        RETURN a.title as title
        LIMIT 1
        """
        result = await self.repo.client.execute_query(query, {"artifact_key": artifact_key})
        if result:
            return result[0].get("title")
        return None

    def _concept_similarity(self, a: set, b: set) -> float:
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def _parse_timestamp(self, ts: Any) -> datetime:
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            ts = ts.replace("Z", "+00:00")
            try:
                return datetime.fromisoformat(ts)
            except Exception:
                pass
        return datetime.now()
