"""
SemanticExtractor - LLM-powered entity extraction from ActivitySlices

Extracts: Topics, Goals, ActionItems, Decisions, Persons from user activity.
Uses vision capabilities for screenshots when available.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from kg_mcp.llm.client import get_llm_client

logger = logging.getLogger(__name__)


# Pydantic models for structured output
class ExtractedTopic(BaseModel):
    name: str = Field(description="Topic name, normalized lowercase")
    confidence: float = Field(default=0.8, ge=0, le=1)


class ExtractedGoal(BaseModel):
    title: str = Field(description="Goal title")
    description: Optional[str] = None
    status: str = Field(default="active")
    priority: int = Field(default=2, ge=1, le=5)


class ExtractedActionItem(BaseModel):
    title: str = Field(description="Action item title")
    description: Optional[str] = None
    due_at: Optional[str] = Field(default=None, description="ISO date if mentioned")
    priority: int = Field(default=2, ge=1, le=5)
    assigned_to: Optional[str] = Field(default=None, description="Person name if mentioned")


class ExtractedDecision(BaseModel):
    text: str = Field(description="Decision text")
    rationale: Optional[str] = None


class ExtractedPerson(BaseModel):
    name: str = Field(description="Person name")
    email: Optional[str] = None
    role: Optional[str] = None


class ExtractedApp(BaseModel):
    name: str = Field(description="App name (e.g. Telegram, Chrome)")
    category: Optional[str] = None


class ExtractedOrganization(BaseModel):
    name: str = Field(description="Organization name")
    type: Optional[str] = None


class ExtractionResult(BaseModel):
    topics: List[ExtractedTopic] = Field(default_factory=list)
    goals: List[ExtractedGoal] = Field(default_factory=list)
    action_items: List[ExtractedActionItem] = Field(default_factory=list)
    decisions: List[ExtractedDecision] = Field(default_factory=list)
    persons: List[ExtractedPerson] = Field(default_factory=list)
    apps: List[ExtractedApp] = Field(default_factory=list)
    organizations: List[ExtractedOrganization] = Field(default_factory=list)
    summary: str = Field(default="")
    confidence: float = Field(default=0.8)


EXTRACTION_PROMPT = """You are a knowledge extraction AI. Analyze the following user activity and extract structured entities.

Activity Context:
- Time: {start_time} to {end_time}
- Apps active: {apps}
- Activity summary: {summary}

Raw Content:
{content}

Extract the following entities IF they exist in the content:
1. TOPICS: Key subjects/domains (e.g., "authentication", "database migration"). Normalized lowercase.
2. GOALS: High-level objectives the user is working toward.
3. ACTION_ITEMS: Specific tasks to be done.
4. DECISIONS: Any decisions made.
5. PERSONS: People mentioned (names, roles).
6. APPS: Software or platforms mentioned (e.g., "Telegram", "Neo4j", "GitHub").
7. ORGANIZATIONS: Companies, groups, or teams mentioned.

Rules:
- Only extract what is EXPLICITLY or STRONGLY IMPLIED.
- **Granularity**: Do not lump everything into a summary. Split distinct entities.
- **Persons**: If a person is mentioned in a specific context (e.g. "Chat with Mario"), extract "Mario" as a Person.
- **Apps**: Extract apps used or mentioned as specific App entities.
- Return valid JSON matching the schema.

Output JSON schema:
{{
  "topics": [{{"name": "string", "confidence": 0.0-1.0}}],
  "goals": [{{"title": "string", "status": "active", "priority": 1-5}}],
  "action_items": [{{"title": "string", "due_at": "ISO date|null", "priority": 1-5, "assigned_to": "string|null"}}],
  "decisions": [{{"text": "string"}}],
  "persons": [{{"name": "string", "email": "string|null", "role": "string|null"}}],
  "apps": [{{"name": "string", "category": "string|null"}}],
  "organizations": [{{"name": "string", "type": "string|null"}}],
  "summary": "Brief structured summary",
  "confidence": 0.0-1.0
}}
"""


class SemanticExtractor:
    """
    Extracts semantic entities from ActivitySlices using LLM.
    """

    def __init__(self, project_id: str):
        self.project_id = project_id
        self.llm_client = get_llm_client()

    async def extract_from_slice(
        self,
        slice_data: Dict[str, Any],
        raw_events: List[Dict[str, Any]],
        artifacts: Optional[List[Dict[str, Any]]] = None
    ) -> ExtractionResult:
        """
        Extract semantic entities from an ActivitySlice.

        Args:
            slice_data: ActivitySlice dict
            raw_events: List of RawEvent dicts in this slice
            artifacts: Optional list of MediaArtifact dicts (screenshots, etc.)

        Returns:
            ExtractionResult with extracted entities
        """
        # Build content from events
        content_parts = []
        for event in raw_events:
            text = event.get("text_content") or ""
            if text:
                content_parts.append(text)

        content = "\n".join(content_parts)

        if not content.strip():
            logger.debug("No content to extract from slice")
            return ExtractionResult(summary=slice_data.get("summary", ""))

        # Prepare prompt
        prompt = EXTRACTION_PROMPT.format(
            start_time=slice_data.get("start_time", ""),
            end_time=slice_data.get("end_time", ""),
            apps=", ".join(slice_data.get("apps", [])),
            summary=slice_data.get("summary", ""),
            content=content[:8000]  # Limit content
        )

        try:
            # Call LLM
            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt="You are a precise entity extraction AI. Output valid JSON only.",
                json_mode=True,
                max_tokens=2000
            )

            # Parse response
            result_dict = json.loads(response)
            result = ExtractionResult(**result_dict)

            logger.info(
                f"Extracted from slice: {len(result.topics)} topics, "
                f"{len(result.goals)} goals, {len(result.action_items)} actions, "
                f"{len(result.decisions)} decisions, {len(result.persons)} persons, "
                f"{len(result.apps)} apps, {len(result.organizations)} organizations"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return ExtractionResult(summary=slice_data.get("summary", ""), confidence=0.3)
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return ExtractionResult(summary=slice_data.get("summary", ""), confidence=0.2)

    async def extract_from_text(self, text: str, context: str = "") -> ExtractionResult:
        """
        Extract entities from raw text (for keystroke buffers, etc.).
        """
        if not text or len(text.strip()) < 10:
            return ExtractionResult()

        prompt = f"""Extract entities from this text:

Context: {context}
Text: {text[:4000]}

Output JSON with topics, goals, action_items, decisions, persons, summary, confidence."""

        try:
            response = await self.llm_client.generate(
                prompt=prompt,
                json_mode=True,
                max_tokens=1500
            )
            result_dict = json.loads(response)
            return ExtractionResult(**result_dict)
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return ExtractionResult()
