"""
InterestScorer - Computes dynamic interest scores for concepts with time decay.
"""
import math
from datetime import datetime
from typing import Any, Dict, List

from kg_mcp.kg.repo import get_repository
from kg_mcp.life.event_taxonomy import EVENT_TYPE_WEIGHTS, DEFAULT_EVENT_WEIGHT


class InterestScorer:
    def __init__(self, project_id: str, tau_days: float = 14.0):
        self.project_id = project_id
        self.repo = get_repository()
        self.tau_days = tau_days

    async def update_interest_scores(self) -> None:
        query = """
        MATCH (re:RawEvent {project_id: $project_id})-[m:MENTIONED]->(t:Topic)
        WHERE re.timestamp >= datetime() - duration('P30D')
        RETURN t.id as id, t.name as name,
               collect({
                   ts: re.timestamp,
                   type: coalesce(re.normalized_type, re.type),
                   confidence: coalesce(m.confidence, 0.8)
               }) as mentions
        """
        records = await self.repo.client.execute_query(query, {"project_id": self.project_id})
        now = datetime.now()

        for record in records:
            mentions = record.get("mentions", [])
            score = 0.0
            for m in mentions:
                ts = self._to_datetime(m.get("ts"))
                delta_days = max((now - ts).total_seconds() / 86400.0, 0.0)
                weight = EVENT_TYPE_WEIGHTS.get(m.get("type"), DEFAULT_EVENT_WEIGHT)
                confidence = m.get("confidence", 0.8)
                score += weight * confidence * math.exp(-delta_days / self.tau_days)

            await self.repo.client.execute_query(
                """
                MATCH (t:Topic {id: $topic_id})
                SET t.interest_score_prev = t.interest_score,
                    t.interest_score = $score,
                    t.interest_updated_at = datetime()
                """,
                {"topic_id": record.get("id"), "score": score}
            )

    def _to_datetime(self, ts: Any) -> datetime:
        if isinstance(ts, datetime):
            return ts
        if hasattr(ts, "isoformat"):
            try:
                return datetime.fromisoformat(ts.isoformat())
            except Exception:
                pass
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                pass
        return datetime.now()
