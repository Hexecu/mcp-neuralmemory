"""
Ingest pipeline for processing user requests.
Orchestrates LLM extraction, linking, and Neo4j commit.
"""

import logging
from typing import Any, Dict, List, Optional

from kg_mcp.llm.client import get_llm_client
from kg_mcp.llm.schemas import ExtractionResult, LinkingResult
from kg_mcp.kg.repo import get_repository

logger = logging.getLogger(__name__)


class IngestPipeline:
    """Pipeline for ingesting user interactions into the knowledge graph."""

    def __init__(self):
        self.llm = get_llm_client()
        self.repo = get_repository()

    async def process_message(
        self,
        project_id: str,
        user_text: str,
        user_id: str = "default_user",
        files: Optional[List[str]] = None,
        diff: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Process a user message through the full pipeline.

        Args:
            project_id: Project ID to associate with this interaction
            user_text: The user's message text
            user_id: User ID for preferences
            files: Optional list of file paths involved
            diff: Optional code diff
            symbols: Optional list of code symbols
            tags: Optional tags for this interaction

        Returns:
            Dict containing interaction_id, extracted entities, and created entity IDs
        """
        logger.info(f"Processing message for project {project_id}")

        # Step 0: Ensure project exists
        await self.repo.get_or_create_project(project_id)

        # Step 1: Create interaction record
        interaction = await self.repo.create_interaction(
            project_id=project_id,
            user_text=user_text,
            tags=tags,
        )
        interaction_id = interaction["id"]
        logger.info(f"Created interaction {interaction_id}")

        # Step 2: Extract entities using LLM
        extraction = await self.llm.extract_entities(
            user_text=user_text,
            files=files,
            diff=diff,
            symbols=symbols,
        )
        logger.info(
            f"Extracted: {len(extraction.goals)} goals, "
            f"{len(extraction.constraints)} constraints, "
            f"{len(extraction.preferences)} preferences, "
            f"{len(extraction.pain_points)} pain points, "
            f"{len(extraction.strategies)} strategies"
        )

        # Step 3: Get existing entities for linking
        existing_goals = await self.repo.get_all_goals(project_id)
        existing_preferences = await self.repo.get_preferences(user_id)
        recent_interactions = await self.repo.get_recent_interactions(project_id, limit=5)

        # Step 4: Link entities using LLM
        linking = await self.llm.link_entities(
            extraction=extraction,
            existing_goals=existing_goals,
            existing_preferences=existing_preferences,
            recent_interactions=recent_interactions,
        )
        logger.info(
            f"Linking: {len(linking.merge_suggestions)} merges, "
            f"{len(linking.relationships)} relationships"
        )

        # Step 5: Commit to Neo4j
        created_entities = await self._commit_to_graph(
            project_id=project_id,
            user_id=user_id,
            interaction_id=interaction_id,
            extraction=extraction,
            linking=linking,
        )

        return {
            "interaction_id": interaction_id,
            "extracted": extraction.model_dump(),
            "linking": linking.model_dump(),
            "created_entities": created_entities,
            "confidence": extraction.confidence,
        }

    async def _commit_to_graph(
        self,
        project_id: str,
        user_id: str,
        interaction_id: str,
        extraction: ExtractionResult,
        linking: LinkingResult,
    ) -> Dict[str, List[str]]:
        """
        Commit extracted entities to Neo4j.

        Returns dict of entity type -> list of created IDs.
        """
        created = {
            "goals": [],
            "constraints": [],
            "preferences": [],
            "pain_points": [],
            "strategies": [],
            "code_artifacts": [],
        }

        # Process merge suggestions first to build ID mapping
        merge_map: Dict[str, str] = {}  # new_title -> existing_id
        for merge in linking.merge_suggestions:
            if merge.confidence >= 0.7:
                merge_map[merge.new_entity_title] = merge.existing_entity_id
                logger.info(
                    f"Merging '{merge.new_entity_title}' into existing "
                    f"'{merge.existing_entity_title}'"
                )

        # Create/update goals
        goal_id_map: Dict[str, str] = {}  # title -> id
        for goal_extract in extraction.goals:
            if goal_extract.title in merge_map:
                goal_id = merge_map[goal_extract.title]
                goal_id_map[goal_extract.title] = goal_id
            else:
                goal = await self.repo.upsert_goal(
                    project_id=project_id,
                    title=goal_extract.title,
                    description=goal_extract.description,
                    status=goal_extract.status,
                    priority=goal_extract.priority,
                )
                goal_id = goal["id"]
                goal_id_map[goal_extract.title] = goal_id
                created["goals"].append(goal_id)

            # Link interaction to goal
            await self.repo.link_interaction_to_goal(interaction_id, goal_id)

        # Create/update constraints
        for constraint_extract in extraction.constraints:
            # Find related goal if mentioned
            related_goal_id = None
            for goal_extract in extraction.goals:
                if goal_extract.title in goal_id_map:
                    related_goal_id = goal_id_map[goal_extract.title]
                    break

            constraint = await self.repo.upsert_constraint(
                project_id=project_id,
                constraint_type=constraint_extract.type,
                description=constraint_extract.description,
                severity=constraint_extract.severity,
                goal_id=related_goal_id,
            )
            created["constraints"].append(constraint["id"])

        # Create/update preferences
        for pref_extract in extraction.preferences:
            pref = await self.repo.upsert_preference(
                user_id=user_id,
                category=pref_extract.category,
                preference=pref_extract.preference,
                strength=pref_extract.strength,
            )
            created["preferences"].append(pref["id"])

        # Create/update pain points
        for pp_extract in extraction.pain_points:
            related_goal_id = None
            if pp_extract.related_goal and pp_extract.related_goal in goal_id_map:
                related_goal_id = goal_id_map[pp_extract.related_goal]

            pp = await self.repo.upsert_painpoint(
                project_id=project_id,
                description=pp_extract.description,
                severity=pp_extract.severity,
                related_goal_id=related_goal_id,
                interaction_id=interaction_id,
            )
            created["pain_points"].append(pp["id"])

        # Create/update strategies
        for strategy_extract in extraction.strategies:
            related_goal_id = None
            if strategy_extract.related_goal and strategy_extract.related_goal in goal_id_map:
                related_goal_id = goal_id_map[strategy_extract.related_goal]

            strategy = await self.repo.upsert_strategy(
                project_id=project_id,
                title=strategy_extract.title,
                approach=strategy_extract.approach,
                rationale=strategy_extract.rationale,
                related_goal_id=related_goal_id,
            )
            created["strategies"].append(strategy["id"])

        # Create code references as artifacts
        for code_ref in extraction.code_references:
            # Find related goals
            related_goal_ids = list(goal_id_map.values())[:3]  # Link to first 3 goals

            artifact = await self.repo.upsert_code_artifact(
                project_id=project_id,
                path=code_ref.path,
                kind="file",
                symbol_fqn=code_ref.symbol,
                start_line=code_ref.start_line,
                end_line=code_ref.end_line,
                related_goal_ids=related_goal_ids if related_goal_ids else None,
            )
            created["code_artifacts"].append(artifact["id"])

        logger.info(f"Committed to graph: {created}")
        return created


# Factory function
_pipeline: Optional[IngestPipeline] = None


def get_ingest_pipeline() -> IngestPipeline:
    """Get or create the ingest pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = IngestPipeline()
    return _pipeline
