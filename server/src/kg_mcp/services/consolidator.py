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

    async def run_dream_cycle(self) -> Dict[str, Any]:
        """
        Execute a subconscious Dream Consolidation cycle across the Knowledge Graph.
        Replays recent events, identifies emergent strategic themes, finds latent connections,
        and generates high-order Reflection nodes on Neo4j.
        """
        from kg_mcp.config import get_settings
        from kg_mcp.llm.vision_analyzer import _robust_json_loads
        from litellm import acompletion
        import json

        settings = get_settings()
        if not settings.llm_enabled:
            return {"status": "skipped", "reason": "llm_disabled"}

        # 1. Fetch graph state for consolidation
        decisions = await self.repo.client.execute_query("""
            MATCH (d:Decision)
            RETURN d.title as title, d.verdict as verdict, d.rationale as rationale,
                   d.subject as subject
            ORDER BY d.decided_at DESC
            LIMIT 15
        """)
        commitments = await self.repo.client.execute_query("""
            MATCH (c:Commitment)
            WHERE c.status = 'open'
            RETURN c.title as title, c.task_description as task, c.due_date_iso as due_date,
                   c.debtor as debtor, c.creditor as creditor
            ORDER BY c.created_at DESC
            LIMIT 15
        """)
        meetings = await self.repo.client.execute_query("""
            MATCH (m:Meeting)
            OPTIONAL MATCH (p:Person)-[:ATTENDED]->(m)
            RETURN m.title as title, m.timestamp as timestamp, collect(DISTINCT p.name) as attendees
            ORDER BY timestamp DESC
            LIMIT 10
        """)
        insights = await self.repo.client.execute_query("""
            MATCH (ins:Insight)
            RETURN ins.topic as topic, ins.takeaway as takeaway, ins.source_url_or_doc as source
            ORDER BY ins.created_at DESC
            LIMIT 10
        """)
        topics = await self.repo.client.execute_query("""
            MATCH (t:Topic)
            RETURN t.name as name
            LIMIT 25
        """)
        people = await self.repo.client.execute_query("""
            MATCH (p:Person)
            RETURN p.name as name
            LIMIT 25
        """)

        total_nodes = len(decisions) + len(commitments) + len(meetings) + len(insights)
        if total_nodes == 0:
            return {"status": "skipped", "reason": "no_memories_to_consolidate"}

        prompt = f"""You are the subconscious Dream Engine of a cognitive personal memory assistant.
During Dream Mode, you consolidate episodic memories into higher-order mental reflections,
strategic patterns, and cross-cutting connections.

WORKING GRAPH STATE:
DECISIONS:
{json.dumps(serialize_response(decisions), ensure_ascii=False, indent=2)}

OPEN COMMITMENTS:
{json.dumps(serialize_response(commitments), ensure_ascii=False, indent=2)}

MEETINGS:
{json.dumps(serialize_response(meetings), ensure_ascii=False, indent=2)}

RESEARCH INSIGHTS:
{json.dumps(serialize_response(insights), ensure_ascii=False, indent=2)}

ACTIVE TOPICS:
{[t['name'] for t in topics]}

PEOPLE INVOLVED:
{[p['name'] for p in people]}

INSTRUCTIONS:
1. Replay and consolidate: identify 2-3 high-level reflections or strategic patterns connecting
   multiple events, people, or decisions.
2. For each reflection, provide:
   - title: concise descriptive title
   - category: strategic | operational | risk | relationship | synthesis
   - synthesis: multi-sentence explanation of the pattern or emergent connection
   - related_topics: list of topic names related to this reflection
   - related_people: list of people involved or mentioned
   - actionable_suggestion: proactive advice or key takeaway for the user
3. Propose cross_entity_links: associative bridges between a person and a topic with nature.

Return a JSON object conforming to:
{{
  "reflections": [
    {{
      "title": "Title",
      "category": "strategic",
      "synthesis": "Synthesis text",
      "related_topics": ["Topic"],
      "related_people": ["Person"],
      "actionable_suggestion": "Suggestion text"
    }}
  ],
  "cross_entity_links": [
    {{
      "person": "Name",
      "topic": "Topic Name",
      "nature": "collaborates_on | specialist_in | negotiated"
    }}
  ]
}}"""

        model = settings.litellm_model if settings.llm_mode == "litellm" else settings.gemini_model
        model = model or settings.llm_model

        completion_kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        if settings.llm_mode == "litellm" and settings.litellm_base_url:
            completion_kwargs["api_base"] = settings.litellm_base_url
            completion_kwargs["api_key"] = settings.litellm_api_key
            completion_kwargs["custom_llm_provider"] = "openai"
        elif settings.gemini_api_key:
            completion_kwargs["api_key"] = settings.gemini_api_key

        try:
            response = await acompletion(**completion_kwargs)
            raw_text = response.choices[0].message.content or "{}"
            dream_data = _robust_json_loads(raw_text)

            created_reflections = []
            for ref in dream_data.get("reflections", []):
                ref_id = str(uuid4())
                await self.repo.client.execute_query(
                    """
                    MATCH (p:Project {id: $project_id})
                    CREATE (r:Reflection:DreamInsight {
                        id: $ref_id,
                        title: $title,
                        category: $category,
                        synthesis: $synthesis,
                        actionable_suggestion: $suggestion,
                        project_id: $project_id,
                        dream_cycle_at: datetime(),
                        created_at: datetime()
                    })
                    MERGE (r)-[:IN_PROJECT]->(p)
                    """,
                    {
                        "project_id": self.project_id,
                        "ref_id": ref_id,
                        "title": ref.get("title", "Reflection"),
                        "category": ref.get("category", "synthesis"),
                        "synthesis": ref.get("synthesis", ""),
                        "suggestion": ref.get("actionable_suggestion", ""),
                    },
                )

                # Link topics
                for t_name in ref.get("related_topics", []):
                    await self.repo.client.execute_query(
                        """
                        MATCH (r:Reflection {id: $ref_id})
                        MERGE (t:Topic {name: $topic_name})
                        MERGE (r)-[:ABOUT_TOPIC]->(t)
                        """,
                        {"ref_id": ref_id, "topic_name": t_name},
                    )

                # Link people
                for p_name in ref.get("related_people", []):
                    await self.repo.client.execute_query(
                        """
                        MATCH (r:Reflection {id: $ref_id})
                        MERGE (person:Person {name: $person_name})
                        MERGE (r)-[:INVOLVES_PERSON]->(person)
                        """,
                        {"ref_id": ref_id, "person_name": p_name},
                    )

                created_reflections.append({
                    "id": ref_id,
                    "title": ref.get("title"),
                    "category": ref.get("category"),
                    "synthesis": ref.get("synthesis"),
                    "suggestion": ref.get("actionable_suggestion"),
                    "related_topics": ref.get("related_topics", []),
                    "related_people": ref.get("related_people", []),
                })

            # Create cross-entity associative links
            cross_links = dream_data.get("cross_entity_links", [])
            for link in cross_links:
                p_name = link.get("person")
                t_name = link.get("topic")
                nature = link.get("nature", "associated_with")
                if p_name and t_name:
                    await self.repo.client.execute_query(
                        """
                        MERGE (p:Person {name: $person_name})
                        MERGE (t:Topic {name: $topic_name})
                        MERGE (p)-[:ASSOCIATED_WITH {nature: $nature, source: 'dream_engine'}]->(t)
                        """,
                        {"person_name": p_name, "topic_name": t_name, "nature": nature},
                    )

            logger.info("Dream cycle generated %d reflections and %d cross-links",
                        len(created_reflections), len(cross_links))

            return {
                "status": "ok",
                "dream_cycle_at": datetime.now(timezone.utc).isoformat(),
                "reflections_count": len(created_reflections),
                "cross_links_count": len(cross_links),
                "reflections": created_reflections,
            }

        except Exception as e:
            logger.error("Dream consolidation cycle failed: %s | Raw text: %s", e, raw_text if 'raw_text' in locals() else 'None')
            return {"status": "error", "error": str(e)}

    async def recall_reflections(
        self,
        category: Optional[str] = None,
        topic: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Recall higher-order reflections and strategic patterns created during Dream Mode."""
        query = """
        MATCH (r:Reflection)
        WHERE ($category IS NULL OR r.category = $category)
          AND ($topic IS NULL OR EXISTS {
              MATCH (r)-[:ABOUT_TOPIC]->(t:Topic)
              WHERE toLower(t.name) CONTAINS toLower($topic)
          })
        OPTIONAL MATCH (r)-[:ABOUT_TOPIC]->(t:Topic)
        OPTIONAL MATCH (r)-[:INVOLVES_PERSON]->(p:Person)
        RETURN r.id as id, r.title as title, r.category as category, r.synthesis as synthesis,
               r.actionable_suggestion as suggestion, r.created_at as created_at,
               collect(DISTINCT t.name) as topics,
               collect(DISTINCT p.name) as people
        ORDER BY created_at DESC
        LIMIT $limit
        """
        try:
            records = await self.repo.client.execute_query(
                query,
                {"category": category, "topic": topic, "limit": limit},
            )
            return serialize_response(records)
        except Exception as e:
            logger.error("recall_reflections failed: %s", e)
            return [{"error": str(e)}]
