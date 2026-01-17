"""
Linker prompt template for entity deduplication and relationship inference.
"""

import json
from typing import Any, Dict, List, Tuple

from kg_mcp.llm.schemas import ExtractionResult


LINKER_SYSTEM_PROMPT = """You are an expert at analyzing knowledge graphs and detecting duplicates/relationships.

Your task is to:
1. DETECT DUPLICATES: Check if any newly extracted entities are duplicates of existing ones
2. SUGGEST MERGES: If entities are the same or very similar, suggest merging them
3. INFER RELATIONSHIPS: Based on context, suggest relationships between entities

RELATIONSHIP TYPES:
- DECOMPOSES_INTO: A goal breaks down into subgoals
- HAS_CONSTRAINT: A goal has a constraint
- HAS_STRATEGY: A goal has a strategy for implementation
- BLOCKED_BY: An entity is blocked by a pain point
- IMPLEMENTED_BY: A goal is implemented by code artifacts
- VERIFIED_BY: A goal is verified by tests
- RELATED_TO: Generic relationship

RULES:
- Only suggest merges with high confidence (> 0.7)
- Consider semantic similarity, not just exact matches
- For relationships, provide clear reasoning
- Use existing entity IDs when available

OUTPUT FORMAT (JSON):
{
  "merge_suggestions": [
    {
      "new_entity_type": "Goal|Preference|etc",
      "new_entity_title": "...",
      "existing_entity_id": "uuid",
      "existing_entity_title": "...",
      "confidence": 0.85,
      "reason": "Why they should be merged"
    }
  ],
  "relationships": [
    {
      "source_type": "Goal",
      "source_id": "uuid or null",
      "source_title": "...",
      "relationship_type": "DECOMPOSES_INTO|HAS_CONSTRAINT|etc",
      "target_type": "SubGoal",
      "target_id": "uuid or null",
      "target_title": "...",
      "confidence": 0.8
    }
  ]
}"""


def get_linker_prompt(
    extraction: ExtractionResult,
    existing_goals: List[Dict[str, Any]],
    existing_preferences: List[Dict[str, Any]],
    recent_interactions: List[Dict[str, Any]],
) -> Tuple[str, str]:
    """
    Build the linker prompt for entity linking and relationship inference.

    Args:
        extraction: The extraction result to link
        existing_goals: List of existing goals from the graph
        existing_preferences: List of existing preferences
        recent_interactions: Recent interactions for context

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    user_prompt_parts = []

    # Add extracted entities
    user_prompt_parts.append("NEWLY EXTRACTED ENTITIES:")
    user_prompt_parts.append(f"```json\n{extraction.model_dump_json(indent=2)}\n```")

    # Add existing goals
    if existing_goals:
        user_prompt_parts.append("\nEXISTING GOALS IN GRAPH:")
        for goal in existing_goals[:20]:  # Limit to 20
            user_prompt_parts.append(
                f"- ID: {goal.get('id')}, Title: {goal.get('title')}, "
                f"Status: {goal.get('status')}"
            )

    # Add existing preferences
    if existing_preferences:
        user_prompt_parts.append("\nEXISTING PREFERENCES:")
        for pref in existing_preferences[:10]:
            user_prompt_parts.append(
                f"- ID: {pref.get('id')}, Category: {pref.get('category')}, "
                f"Preference: {pref.get('preference')}"
            )

    # Add recent interaction context
    if recent_interactions:
        user_prompt_parts.append("\nRECENT INTERACTIONS (for context):")
        for interaction in recent_interactions[:5]:
            user_prompt_parts.append(
                f"- {interaction.get('timestamp', 'N/A')}: "
                f"{interaction.get('user_text', '')[:100]}..."
            )

    user_prompt_parts.append(
        "\n\nAnalyze the newly extracted entities against the existing graph. "
        "Suggest merges for duplicates and infer relationships. "
        "Return a JSON object following the specified format."
    )

    return LINKER_SYSTEM_PROMPT, "\n".join(user_prompt_parts)
