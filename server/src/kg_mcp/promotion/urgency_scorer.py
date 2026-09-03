"""
UrgencyScorer - Computes urgency scores for ActionItems

Factors:
- Due date proximity
- Stalled time (no activity)
- Priority weight
- Topic recency (if topic is being worked on)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from kg_mcp.kg.repo import get_repository

logger = logging.getLogger(__name__)


class UrgencyScorer:
    """
    Computes urgency scores for ActionItems based on multiple factors.

    Score range: 0-100 (higher = more urgent)
    """

    # Weight factors
    WEIGHT_DUE_PROXIMITY = 0.4
    WEIGHT_STALLED = 0.25
    WEIGHT_PRIORITY = 0.2
    WEIGHT_TOPIC_RECENCY = 0.15

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.repo = get_repository()

    async def score_action_item(self, action_id: str) -> float:
        """
        Compute urgency score for a single ActionItem.
        """
        # Fetch action details
        query = """
        MATCH (ai:ActionItem {id: $action_id})
        OPTIONAL MATCH (ai)-[:ABOUT]->(t:Topic)
        RETURN ai {.*} as action,
               t.last_seen_at as topic_last_seen,
               t.frequency_7d as topic_frequency
        """

        records = await self.repo.client.execute_query(
            query, {"action_id": action_id}
        )

        if not records:
            return 0.0

        record = records[0]
        action = record.get("action", {})
        topic_last_seen = record.get("topic_last_seen")
        topic_frequency = record.get("topic_frequency", 0)

        return self._compute_score(
            action,
            topic_last_seen,
            topic_frequency
        )

    async def score_all_open_actions(self) -> List[Dict[str, Any]]:
        """
        Compute urgency scores for all open ActionItems in project.

        Returns:
            List of {action_id, title, urgency_score} dicts
        """
        query = """
        MATCH (ai:ActionItem {project_id: $project_id})
        WHERE ai.status IN ['open', 'in_progress']
        OPTIONAL MATCH (ai)-[:ABOUT]->(t:Topic)
        RETURN ai.id as action_id,
               ai.title as title,
               ai.due_at as due_at,
               ai.priority as priority,
               ai.last_touched_at as last_touched,
               ai.created_at as created_at,
               t.last_seen_at as topic_last_seen,
               t.frequency_7d as topic_frequency
        """

        records = await self.repo.client.execute_query(
            query, {"project_id": self.project_id}
        )

        scored_actions = []
        for record in records:
            action = {
                "due_at": record.get("due_at"),
                "priority": record.get("priority", 2),
                "last_touched_at": record.get("last_touched"),
                "created_at": record.get("created_at"),
            }

            score = self._compute_score(
                action,
                record.get("topic_last_seen"),
                record.get("topic_frequency", 0)
            )

            scored_actions.append({
                "action_id": record.get("action_id"),
                "title": record.get("title"),
                "urgency_score": score
            })

        return sorted(scored_actions, key=lambda x: x["urgency_score"], reverse=True)

    async def update_all_scores(self) -> int:
        """
        Batch update urgency scores for all open ActionItems.

        Returns:
            Number of actions updated
        """
        scored = await self.score_all_open_actions()

        update_query = """
        UNWIND $items as item
        MATCH (ai:ActionItem {id: item.action_id})
        SET ai.urgency_score = item.urgency_score
        """

        await self.repo.client.execute_query(
            update_query,
            {"items": scored}
        )

        logger.info(f"Updated urgency scores for {len(scored)} action items")
        return len(scored)

        if topic_frequency and topic_frequency > 5:
            topic_score = min(100, topic_score + 20)

        # Weighted sum
        total_score = (
            self.WEIGHT_DUE_PROXIMITY * due_score +
            self.WEIGHT_STALLED * stalled_score +
            self.WEIGHT_PRIORITY * priority_score +
            self.WEIGHT_TOPIC_RECENCY * topic_score
        )

        return round(total_score, 2)

    def _to_datetime(self, value: Any) -> Optional[datetime]:
        """Safely convert any timestamp format to native datetime."""
        if not value:
            return None

        if isinstance(value, datetime):
            return value.replace(tzinfo=None)

        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
            except:
                return None

        # Handle Neo4j DateTime/Date objects
        if hasattr(value, "iso_format"):
            # Neo4j 5.x driver objects often have iso_format or similar
            try:
                # Try standard conversion first
                return datetime.fromisoformat(value.iso_format()).replace(tzinfo=None)
            except:
                pass

        # Fallback: try converting to string and parsing
        try:
            s = str(value)
            return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        except:
            return None

    def _compute_score(
        self,
        action: Dict[str, Any],
        topic_last_seen: Any,
        topic_frequency: int
    ) -> float:
        """
        Compute weighted urgency score.
        """
        try:
            now = datetime.now()

            # 1. Due proximity score
            due_score = 0
            due_at = self._to_datetime(action.get("due_at"))

            if due_at:
                days_until_due = (due_at - now).days
                if days_until_due < 0:
                    due_score = 100  # Overdue
                elif days_until_due == 0:
                    due_score = 95
                elif days_until_due == 1:
                    due_score = 85
                elif days_until_due <= 3:
                    due_score = 70
                elif days_until_due <= 7:
                    due_score = 50
                elif days_until_due <= 14:
                    due_score = 30
                else:
                    due_score = 10

            # 2. Stalled score (no activity)
            stalled_score = 0
            last_touched = self._to_datetime(action.get("last_touched_at") or action.get("created_at"))

            if last_touched:
                days_stalled = (now - last_touched).days
                if days_stalled >= 14:
                    stalled_score = 80
                elif days_stalled >= 7:
                    stalled_score = 60
                elif days_stalled >= 3:
                    stalled_score = 40
                elif days_stalled >= 1:
                    stalled_score = 20

            # 3. Priority score
            priority = action.get("priority", 2)
            priority_score = {1: 100, 2: 60, 3: 40, 4: 20, 5: 10}.get(priority, 50)

            # 4. Topic recency score (boost if topic is active)
            topic_score = 0
            topic_last_seen = self._to_datetime(topic_last_seen)

            if topic_last_seen:
                days_since_topic = (now - topic_last_seen).days
                if days_since_topic == 0:
                    topic_score = 100  # Currently working on this topic
                elif days_since_topic <= 1:
                    topic_score = 70
                elif days_since_topic <= 3:
                    topic_score = 40
                elif days_since_topic <= 7:
                    topic_score = 20

            # Boost based on topic frequency
            if topic_frequency and topic_frequency > 5:
                topic_score = min(100, topic_score + 20)

            # Weighted sum
            total_score = (
                self.WEIGHT_DUE_PROXIMITY * due_score +
                self.WEIGHT_STALLED * stalled_score +
                self.WEIGHT_PRIORITY * priority_score +
                self.WEIGHT_TOPIC_RECENCY * topic_score
            )

            return round(total_score, 2)

        except Exception as e:
            logger.error(f"Error computing score for action {action.get('id', 'unknown')}: {e}")
            return 0.0
