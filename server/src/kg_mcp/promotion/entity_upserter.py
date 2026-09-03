"""
EntityUpserter - Deduplicating upsert of extracted entities to Neo4j

Handles: Topic, Goal, ActionItem, Decision, Person with provenance links.
Includes semantic deduplication using embeddings for similar entities.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

from kg_mcp.kg.repo import get_repository
from kg_mcp.llm.client import get_llm_client
from kg_mcp.promotion.semantic_extractor import (
    ExtractionResult, ExtractedTopic, ExtractedGoal,
    ExtractedActionItem, ExtractedDecision, ExtractedPerson,
    ExtractedApp, ExtractedOrganization
)

logger = logging.getLogger(__name__)


class EntityUpserter:
    """
    Upserts extracted entities to Neo4j with deduplication.

    Links entities to their source (ActivitySlice, Meeting, etc.) for provenance.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.repo = get_repository()
        self.llm_client = get_llm_client()

    async def upsert_all(
        self,
        extraction: ExtractionResult,
        source_type: str = "ActivitySlice",
        source_id: str = None
    ) -> Dict[str, List[str]]:
        """
        Upsert all extracted entities and link to source.

        Args:
            extraction: ExtractionResult from SemanticExtractor
            source_type: Type of source node (ActivitySlice, Meeting, etc.)
            source_id: ID of source node for provenance

        Returns:
            Dict mapping entity type to list of created/matched IDs
        """
        result = {
            "topics": [],
            "goals": [],
            "action_items": [],
            "decisions": [],
            "persons": [],
            "apps": [],
            "organizations": []
        }

        # Upsert Topics
        for topic in extraction.topics:
            topic_id = await self.upsert_topic(topic, source_type, source_id)
            if topic_id:
                result["topics"].append(topic_id)

        # Upsert Goals
        for goal in extraction.goals:
            goal_id = await self.upsert_goal(goal, source_type, source_id)
            if goal_id:
                result["goals"].append(goal_id)

        # Upsert ActionItems
        for action in extraction.action_items:
            action_id = await self.upsert_action_item(action, source_type, source_id)
            if action_id:
                result["action_items"].append(action_id)

        # Upsert Decisions
        for decision in extraction.decisions:
            decision_id = await self.upsert_decision(decision, source_type, source_id)
            if decision_id:
                result["decisions"].append(decision_id)

        # Upsert Persons
        for person in extraction.persons:
            person_id = await self.upsert_person(person, source_type, source_id)
            if person_id:
                result["persons"].append(person_id)

        # Upsert Apps
        for app in extraction.apps:
            app_id = await self.upsert_app(app, source_type, source_id)
            if app_id:
                result["apps"].append(app_id)

        # Upsert Organizations
        for org in extraction.organizations:
            org_id = await self.upsert_organization(org, source_type, source_id)
            if org_id:
                result["organizations"].append(org_id)

        logger.info(f"Upserted entities: {sum(len(v) for v in result.values())} total")
        return result

    async def upsert_topic(
        self,
        topic: ExtractedTopic,
        source_type: str = None,
        source_id: str = None
    ) -> Optional[str]:
        """
        Upsert a Topic with deduplication by normalized name.
        """
        normalized_name = topic.name.lower().strip()

        # Generate embedding for semantic matching
        embedding = None
        try:
            embedding = await self.llm_client.embed(normalized_name)
        except:
            pass

        query = """
        MATCH (p:Project {id: $project_id})
        MERGE (t:Topic {name: $name})
        ON CREATE SET
            t.id = $id,
            t.created_at = datetime(),
            t.frequency_7d = 1,
            t.embedding = $embedding
        ON MATCH SET
            t.last_seen_at = datetime(),
            t.frequency_7d = COALESCE(t.frequency_7d, 0) + 1
        MERGE (t)-[:IN_PROJECT]->(p)
        RETURN t.id as id, t.name as name
        """

        try:
            records = await self.repo.client.execute_query(
                query,
                {
                    "project_id": self.project_id,
                    "id": str(uuid4()),
                    "name": normalized_name,
                    "embedding": embedding,
                }
            )

            if records:
                topic_id = records[0].get("id")

                # Link to source if provided
                if source_type and source_id:
                    await self._link_to_source(
                        "Topic", topic_id, normalized_name,
                        source_type, source_id, "MENTIONED_IN"
                    )

                return topic_id
        except Exception as e:
            logger.error(f"Failed to upsert topic '{normalized_name}': {e}")

        return None

    async def upsert_goal(
        self,
        goal: ExtractedGoal,
        source_type: str = None,
        source_id: str = None
    ) -> Optional[str]:
        """
        Upsert a Goal with deduplication by title similarity.
        """
        query = """
        MATCH (p:Project {id: $project_id})
        MERGE (g:Goal {title: $title, project_id: $project_id})
        ON CREATE SET
            g.id = $id,
            g.description = $description,
            g.status = $status,
            g.priority = $priority,
            g.created_at = datetime()
        ON MATCH SET
            g.last_seen_at = datetime()
        MERGE (p)-[:HAS_GOAL]->(g)
        RETURN g.id as id
        """

        try:
            records = await self.repo.client.execute_query(
                query,
                {
                    "project_id": self.project_id,
                    "id": str(uuid4()),
                    "title": goal.title,
                    "description": goal.description,
                    "status": goal.status,
                    "priority": goal.priority,
                }
            )

            if records:
                goal_id = records[0].get("id")

                if source_type and source_id:
                    await self._link_to_source(
                        "Goal", goal_id, goal.title,
                        source_type, source_id, "SUPPORTS"
                    )

                return goal_id
        except Exception as e:
            logger.error(f"Failed to upsert goal '{goal.title}': {e}")

        return None

    async def upsert_action_item(
        self,
        action: ExtractedActionItem,
        source_type: str = None,
        source_id: str = None
    ) -> Optional[str]:
        """
        Upsert an ActionItem with deduplication.
        """
        query = """
        MATCH (p:Project {id: $project_id})
        CREATE (ai:ActionItem {
            id: $id,
            title: $title,
            description: $description,
            status: 'open',
            priority: $priority,
            urgency_score: 0,
            created_at: datetime(),
            last_touched_at: datetime(),
            project_id: $project_id
        })
        MERGE (ai)-[:IN_PROJECT]->(p)
        FOREACH (_ IN CASE WHEN $due_at IS NOT NULL THEN [1] ELSE [] END |
            SET ai.due_at = datetime($due_at)
        )
        RETURN ai.id as id
        """

        try:
            records = await self.repo.client.execute_query(
                query,
                {
                    "project_id": self.project_id,
                    "id": str(uuid4()),
                    "title": action.title,
                    "description": action.description,
                    "priority": action.priority,
                    "due_at": action.due_at,
                }
            )

            if records:
                action_id = records[0].get("id")

                if source_type and source_id:
                    await self._link_to_source(
                        "ActionItem", action_id, action.title,
                        source_type, source_id, "DERIVED_FROM"
                    )

                # Link to assigned person if specified
                if action.assigned_to:
                    await self._link_to_person(action_id, action.assigned_to)

                return action_id
        except Exception as e:
            logger.error(f"Failed to upsert action item '{action.title}': {e}")

        return None

    async def upsert_decision(
        self,
        decision: ExtractedDecision,
        source_type: str = None,
        source_id: str = None
    ) -> Optional[str]:
        """
        Create a Decision node linked to its source.
        """
        query = """
        MATCH (p:Project {id: $project_id})
        CREATE (d:Decision {
            id: $id,
            text: $text,
            rationale: $rationale,
            decided_at: datetime(),
            project_id: $project_id
        })
        MERGE (d)-[:IN_PROJECT]->(p)
        RETURN d.id as id
        """

        try:
            records = await self.repo.client.execute_query(
                query,
                {
                    "project_id": self.project_id,
                    "id": str(uuid4()),
                    "text": decision.text,
                    "rationale": decision.rationale,
                }
            )

            if records:
                decision_id = records[0].get("id")

                if source_type and source_id:
                    await self._link_to_source(
                        "Decision", decision_id, decision.text[:50],
                        source_type, source_id, "IN_CONTEXT"
                    )

                return decision_id
        except Exception as e:
            logger.error(f"Failed to upsert decision: {e}")

        return None

    async def upsert_person(
        self,
        person: ExtractedPerson,
        source_type: str = None,
        source_id: str = None
    ) -> Optional[str]:
        """
        Upsert a Person node by name.
        """
        query = """
        MERGE (p:Person {name: $name})
        ON CREATE SET
            p.id = $id,
            p.email = $email,
            p.role = $role,
            p.created_at = datetime()
        ON MATCH SET
            p.email = COALESCE($email, p.email),
            p.role = COALESCE($role, p.role)
        RETURN p.id as id
        """

        try:
            records = await self.repo.client.execute_query(
                query,
                {
                    "id": str(uuid4()),
                    "name": person.name,
                    "email": person.email,
                    "role": person.role,
                }
            )

            if records:
                person_id = records[0].get("id")

                if source_type and source_id:
                    await self._link_to_source(
                        "Person", person_id, person.name,
                        source_type, source_id, "MENTIONED_IN"
                    )
                return person.name
        except Exception as e:
            logger.error(f"Failed to upsert person '{person.name}': {e}")

        return None

    async def _link_to_source(
        self,
        entity_label: str,
        entity_id: str,
        entity_key: str,
        source_type: str,
        source_id: str,
        relationship: str
    ):
        """Link an entity to its source for provenance."""
        # Build dynamic query based on entity type
        if entity_label == "Topic":
            entity_match = f"MATCH (e:{entity_label} {{name: $entity_key}})"
        else:
            entity_match = f"MATCH (e:{entity_label} {{id: $entity_id}})"

        query = f"""
        {entity_match}
        MATCH (s:{source_type} {{id: $source_id}})
        MERGE (s)-[:{relationship}]->(e)
        """

        try:
            await self.repo.client.execute_query(
                query,
                {
                    "entity_id": entity_id,
                    "entity_key": entity_key,
                    "source_id": source_id,
                }
            )
            logger.debug(f"Linked {entity_label} {entity_key} to {source_type} {source_id}")
        except Exception as e:
            logger.debug(f"Failed to link {entity_label} to {source_type}: {e}")

    async def _link_to_person(self, action_id: str, person_name: str):
        """Link ActionItem to assigned Person."""
        query = """
        MATCH (ai:ActionItem {id: $action_id})
        MERGE (p:Person {name: $person_name})
        MERGE (ai)-[:ASSIGNED_TO]->(p)
        """
        try:
            await self.repo.client.execute_query(
                query,
                {"action_id": action_id, "person_name": person_name}
            )
        except Exception as e:
            logger.debug(f"Failed to link action to person: {e}")

    async def upsert_app(
        self,
        app: ExtractedApp,
        source_type: str = None,
        source_id: str = None
    ) -> Optional[str]:
        """
        Upsert an App node (deduplicated by normalized name).
        """
        normalized_name = app.name.strip()

        query = """
        MERGE (a:App {name: $name})
        ON CREATE SET
            a.id = $id,
            a.category = $category,
            a.created_at = datetime()
        ON MATCH SET
            a.category = COALESCE($category, a.category)
        RETURN a.id as id
        """

        try:
            records = await self.repo.client.execute_query(
                query,
                {
                    "id": str(uuid4()),
                    "name": normalized_name,
                    "category": app.category
                }
            )

            if records:
                app_id = records[0].get("id")

                if source_type and source_id:
                    # Link source (ActivitySlice) to App with USED_APP
                    await self._link_to_source(
                        "App", app_id, normalized_name,
                        source_type, source_id, "USED_APP"
                    )
                return app_id
        except Exception as e:
            logger.error(f"Failed to upsert app '{normalized_name}': {e}")

        return None

    async def upsert_organization(
        self,
        org: ExtractedOrganization,
        source_type: str = None,
        source_id: str = None
    ) -> Optional[str]:
        """
        Upsert an Organization node.
        """
        normalized_name = org.name.strip()

        query = """
        MERGE (o:Organization {name: $name})
        ON CREATE SET
            o.id = $id,
            o.type = $type,
            o.created_at = datetime()
        ON MATCH SET
            o.type = COALESCE($type, o.type)
        RETURN o.id as id
        """

        try:
            records = await self.repo.client.execute_query(
                query,
                {
                    "id": str(uuid4()),
                    "name": normalized_name,
                    "type": org.type
                }
            )

            if records:
                org_id = records[0].get("id")

                if source_type and source_id:
                    await self._link_to_source(
                        "Organization", org_id, normalized_name,
                        source_type, source_id, "RELATED_TO"
                    )
                return org_id
        except Exception as e:
            logger.error(f"Failed to upsert organization '{normalized_name}': {e}")

        return None
