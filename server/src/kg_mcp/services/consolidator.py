"""
MemoryConsolidator - Nightly/Periodic consolidation and sleep engine.
Merges raw interaction fragments into episodes, resolves duplicate entities,
prunes ephemeral raw logs, and generates daily executive briefings.
"""
import logging
from datetime import datetime, timezone, date
from typing import Any, Dict, List, Optional
from uuid import uuid4

from kg_mcp.kg.repo import get_repository
from kg_mcp.utils import serialize_response

logger = logging.getLogger(__name__)


class MemoryConsolidator:
    """Manages memory compaction, entity deduplication, and retention pruning."""

    def __init__(self, project_id: str = "default"):
        self.project_id = project_id
        self.repo = get_repository()

    async def prune_ephemeral_events(self, retention_days: int = 2) -> int:
        """
        Prune ephemeral RawEvent nodes older than retention_days.
        Preserves all higher-level semantic nodes (Decision, Commitment, Meeting, Artifact, Topic).
        """
        query = """
        MATCH (r:RawEvent)
        WHERE r.created_at < datetime() - duration({days: $days})
          AND NOT (r)<-[:DERIVED_FROM]-(:Decision)
          AND NOT (r)<-[:DERIVED_FROM]-(:Commitment)
          AND NOT (r)<-[:RECORDED_IN]-(:Meeting)
        WITH r LIMIT 500
        DETACH DELETE r
        RETURN count(r) as deleted_count
        """
        try:
            res = await self.repo.client.execute_query(query, {"days": int(retention_days)})
            count = res[0]["deleted_count"] if res else 0
            logger.info("Pruned %d ephemeral raw events older than %d days", count, retention_days)
            return count
        except Exception as e:
            logger.error("Error during ephemeral event pruning: %s", e)
            return 0

    async def deduplicate_topics(self, similarity_threshold: float = 0.90) -> int:
        """
        Find and merge synonym/duplicate Topics within the project.
        """
        query = """
        MATCH (t1:Topic), (t2:Topic)
        WHERE id(t1) < id(t2)
          AND (toLower(t1.name) = toLower(t2.name)
               OR (t1.name CONTAINS t2.name AND size(t2.name) > 4)
               OR (t2.name CONTAINS t1.name AND size(t1.name) > 4))
        RETURN t1.name as master_name, t2.name as alias_name, t1.id as master_id, t2.id as alias_id
        LIMIT 50
        """
        merged_count = 0
        try:
            pairs = await self.repo.client.execute_query(query)
            for pair in pairs:
                master_name = pair["master_name"]
                alias_name = pair["alias_name"]
                merge_cypher = """
                MATCH (master:Topic {name: $master_name})
                MATCH (alias:Topic {name: $alias_name})
                OPTIONAL MATCH (alias)<-[r:MENTIONED]-(re:RawEvent)
                FOREACH (_ IN CASE WHEN re IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (re)-[:MENTIONED]->(master)
                )
                OPTIONAL MATCH (alias)<-[r2:ABOUT_TOPIC]-(d:Decision)
                FOREACH (_ IN CASE WHEN d IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (d)-[:ABOUT_TOPIC]->(master)
                )
                DETACH DELETE alias
                """
                await self.repo.client.execute_query(
                    merge_cypher,
                    {"master_name": master_name, "alias_name": alias_name},
                )
                merged_count += 1
            logger.info("Deduplicated %d synonymous topics", merged_count)
            return merged_count
        except Exception as e:
            logger.error("Error deduplicating topics: %s", e)
            return 0

    async def generate_daily_briefing(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive executive briefing for a specific date (defaults to today).
        Summarizes decisions made, open commitments, meetings, and key research topics.
        """
        if not target_date:
            target_date = date.today().isoformat()

        decisions_query = """
        MATCH (d:Decision)
        WHERE substring(toString(d.decided_at), 0, 10) = $date
        OPTIONAL MATCH (d)-[:TOWARDS_PERSON]->(p:Person)
        OPTIONAL MATCH (d)-[:ON_ARTIFACT]->(a:Artifact)
        RETURN d.title as title, d.verdict as verdict, d.rationale as rationale,
               p.name as counterparty, a.title as artifact_title
        ORDER BY d.decided_at DESC
        """

        commitments_query = """
        MATCH (c:Commitment)
        WHERE substring(toString(c.created_at), 0, 10) = $date OR c.status = 'open'
        OPTIONAL MATCH (c)-[:PROMISED_TO]->(p1:Person)
        OPTIONAL MATCH (c)-[:PROMISED_BY]->(p2:Person)
        RETURN c.title as title, c.task_description as task, c.due_date_iso as due_date,
               c.status as status, c.debtor as debtor,
               p1.name as creditor_name, p2.name as debtor_name
        ORDER BY c.created_at DESC
        """

        meetings_query = """
        MATCH (m:Meeting)
        WHERE substring(toString(m.timestamp), 0, 10) = $date
        OPTIONAL MATCH (p:Person)-[:ATTENDED]->(m)
        OPTIONAL MATCH (m)-[:DISCUSSED]->(t:Topic)
        RETURN m.title as title, m.duration as duration,
               collect(DISTINCT p.name) as participants,
               collect(DISTINCT t.name) as topics
        """

        insights_query = """
        MATCH (ins:Insight)
        WHERE substring(toString(ins.created_at), 0, 10) = $date
        RETURN ins.topic as topic, ins.takeaway as takeaway, ins.source_url_or_doc as source
        """

        try:
            decisions = await self.repo.client.execute_query(decisions_query, {"date": target_date})
            commitments = await self.repo.client.execute_query(commitments_query, {"date": target_date})
            meetings = await self.repo.client.execute_query(meetings_query, {"date": target_date})
            insights = await self.repo.client.execute_query(insights_query, {"date": target_date})

            briefing = {
                "date": target_date,
                "project_id": self.project_id,
                "summary_counts": {
                    "decisions_count": len(decisions),
                    "commitments_count": len(commitments),
                    "meetings_count": len(meetings),
                    "research_insights_count": len(insights),
                },
                "decisions": decisions,
                "commitments": commitments,
                "meetings": meetings,
                "research_insights": insights,
            }
            return serialize_response(briefing)
        except Exception as e:
            logger.error("Error generating daily briefing: %s", e)
            return {"error": str(e), "date": target_date}
