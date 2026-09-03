"""
SegmentBuilder - Builds semantic activity segments from RawEvents.
"""
import json
import logging
from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from kg_mcp.config import get_settings

logger = logging.getLogger(__name__)


class SegmentBuilder:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.settings = get_settings()

    def build_segments_from_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not events:
            return []

        sorted_events = sorted(events, key=lambda e: self._parse_timestamp(e.get("timestamp")))
        segments: List[Dict[str, Any]] = []

        current: Dict[str, Any] = {}

        for event in sorted_events:
            event_ts = self._parse_timestamp(event.get("timestamp"))
            if not current:
                current = self._init_segment(event, event_ts)
                continue

            if self._should_break(current, event, event_ts):
                segments.append(self._finalize_segment(current))
                current = self._init_segment(event, event_ts)
            else:
                self._append_event(current, event, event_ts)

        if current:
            segments.append(self._finalize_segment(current))

        return segments

    def _init_segment(self, event: Dict[str, Any], event_ts: datetime) -> Dict[str, Any]:
        app = self._get_event_app(event)
        concepts = self._get_event_concepts(event)
        artifact_id = self._get_event_artifact(event)
        event_type = self._get_event_type(event)

        segment = {
            "id": str(uuid4()),
            "project_id": self.project_id,
            "start_time": event_ts,
            "end_time": event_ts,
            "event_ids": [event.get("id")],
            "apps": set([app]) if app else set(),
            "concepts": Counter(concepts),
            "artifact_canonical_ids": set([artifact_id]) if artifact_id else set(),
            "event_types": set([event_type]) if event_type else set(),
            "duplicate_count": 1 if event.get("is_duplicate") else 0,
            "summaries": [event.get("analysis_summary")] if event.get("analysis_summary") else [],
        }
        return segment

    def _append_event(self, segment: Dict[str, Any], event: Dict[str, Any], event_ts: datetime) -> None:
        segment["end_time"] = event_ts
        segment["event_ids"].append(event.get("id"))
        app = self._get_event_app(event)
        if app:
            segment["apps"].add(app)
        for concept in self._get_event_concepts(event):
            segment["concepts"][concept] += 1
        artifact_id = self._get_event_artifact(event)
        if artifact_id:
            segment["artifact_canonical_ids"].add(artifact_id)
        event_type = self._get_event_type(event)
        if event_type:
            segment["event_types"].add(event_type)
        if event.get("is_duplicate"):
            segment["duplicate_count"] += 1
        if event.get("analysis_summary"):
            segment["summaries"].append(event.get("analysis_summary"))

    def _finalize_segment(self, segment: Dict[str, Any]) -> Dict[str, Any]:
        concepts = [c for c, _ in segment["concepts"].most_common(5)]
        primary_concept = concepts[0] if concepts else None
        apps = list(segment["apps"])
        primary_app = apps[0] if apps else None
        artifacts = list(segment["artifact_canonical_ids"])
        primary_artifact = artifacts[0] if artifacts else None

        summary = self._build_summary(segment.get("summaries", []), primary_app, primary_artifact, concepts)
        event_types = list(segment["event_types"])

        return {
            "id": segment["id"],
            "project_id": segment["project_id"],
            "start_time": segment["start_time"].isoformat(),
            "end_time": segment["end_time"].isoformat(),
            "summary": summary,
            "event_count": len(segment["event_ids"]),
            "event_ids": segment["event_ids"],
            "apps": apps,
            "concepts": concepts,
            "artifact_canonical_ids": artifacts,
            "event_types": event_types,
            "primary_app": primary_app,
            "primary_artifact_id": primary_artifact,
            "primary_concept": primary_concept,
            "duplicate_count": segment["duplicate_count"],
            "confidence": 0.8,
            "segment_kind": "semantic",
        }

    def _should_break(self, current: Dict[str, Any], event: Dict[str, Any], event_ts: datetime) -> bool:
        last_ts = current["end_time"]
        gap = event_ts - last_ts
        if gap > timedelta(minutes=self.settings.segment_gap_minutes):
            return True

        event_type = self._get_event_type(event)
        if event_type in ("CONTEXT_SWITCH", "MEETING"):
            return True

        event_artifact = self._get_event_artifact(event)
        current_artifacts = current["artifact_canonical_ids"]
        if event_artifact and current_artifacts and event_artifact not in current_artifacts:
            similarity = self._concept_similarity(
                set(current["concepts"].keys()),
                set(self._get_event_concepts(event))
            )
            if similarity < 0.2:
                return True

        event_app = self._get_event_app(event)
        if event_app and current["apps"] and event_app not in current["apps"]:
            similarity = self._concept_similarity(
                set(current["concepts"].keys()),
                set(self._get_event_concepts(event))
            )
            if similarity < 0.2:
                return True

        return False

    def _build_summary(
        self,
        summaries: List[str],
        app: Optional[str],
        artifact_id: Optional[str],
        concepts: List[str],
    ) -> str:
        if summaries:
            return summaries[0]
        parts = []
        if artifact_id:
            parts.append(f"Artifact: {artifact_id}")
        if concepts:
            parts.append("Topics: " + ", ".join(concepts[:3]))
        if app:
            parts.append(f"App: {app}")
        return " | ".join(parts) if parts else "Activity segment"

    def _get_event_app(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get("app"):
            return event.get("app")
        data = self._load_data(event)
        return data.get("app")

    def _get_event_artifact(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get("artifact_canonical_id"):
            return event.get("artifact_canonical_id")
        data = self._load_data(event)
        return data.get("artifact_canonical_id")

    def _get_event_type(self, event: Dict[str, Any]) -> Optional[str]:
        if event.get("normalized_type"):
            return event.get("normalized_type")
        data = self._load_data(event)
        return data.get("normalized_type")

    def _get_event_concepts(self, event: Dict[str, Any]) -> List[str]:
        concepts = event.get("concepts")
        if isinstance(concepts, list):
            return [c for c in concepts if isinstance(c, str)]
        data = self._load_data(event)
        concepts = data.get("concepts", [])
        if isinstance(concepts, list):
            return [c for c in concepts if isinstance(c, str)]
        return []

    def _load_data(self, event: Dict[str, Any]) -> Dict[str, Any]:
        data = event.get("data", {})
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                data = {}
        return data if isinstance(data, dict) else {}

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
