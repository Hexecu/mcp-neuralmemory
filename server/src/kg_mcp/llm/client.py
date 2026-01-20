"""
LLM Client wrapper for Gemini via LiteLLM.
Provides structured extraction and linking capabilities.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import litellm
from pydantic import ValidationError

from kg_mcp.config import get_settings
from kg_mcp.llm.schemas import (
    ExtractionResult,
    LinkingResult,
    CodeReference,
    GoalExtract,
    ConstraintExtract,
    PreferenceExtract,
    PainPointExtract,
    StrategyExtract,
    AcceptanceCriteriaExtract,
    MergeSuggestion,
    RelationshipSuggestion,
)
from kg_mcp.llm.prompts.extractor import get_extractor_prompt
from kg_mcp.llm.prompts.linker import get_linker_prompt

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for LLM operations using LiteLLM."""

    def __init__(self):
        self.settings = get_settings()

        # Determine active mode and primary provider
        mode = self.settings.llm_mode
        primary = self.settings.llm_primary

        if mode == "gemini_direct" or (mode == "both" and primary == "gemini_direct"):
            self._configure_gemini_direct()
        elif mode == "litellm" or (mode == "both" and primary == "litellm"):
            self._configure_litellm()
        else:
            # Fallback (legacy behavior)
            if self.settings.litellm_base_url and self.settings.litellm_api_key:
                self._configure_litellm()
            elif self.settings.gemini_api_key:
                self._configure_gemini_direct()
            else:
                self.api_base = None
                self.api_key = None
                self.model = self.settings.llm_model  # fallback
                logger.warning("No LLM API credentials configured!")

    def _configure_gemini_direct(self):
        """Configure for Gemini Direct API."""
        self.provider = "gemini"
        self.api_base = None
        self.api_key = self.settings.gemini_api_key
        # For Gemini Direct via LiteLLM library, we might need to set the environment variable
        # or pass it explicitly. LiteLLM supports 'gemini/' prefix with GEMINI_API_KEY env.
        litellm.api_key = self.settings.gemini_api_key
        
        # Use specific gemini model if set, else fallback
        self.model = self.settings.gemini_model or self.settings.llm_model
        
        # If model doesn't start with gemini/, prepend it for LiteLLM
        if not self.model.startswith("gemini/") and "gemini" in self.model:
             self.model = f"gemini/{self.model}"
             
        logger.info(f"Using Direct Gemini API with model {self.model}")

    def _configure_litellm(self):
        """Configure for LiteLLM Gateway."""
        self.provider = "litellm"
        self.api_base = self.settings.litellm_base_url.rstrip("/")
        self.api_key = self.settings.litellm_api_key
        
        # Use specific litellm model if set, else fallback
        self.model = self.settings.litellm_model or self.settings.llm_model
        logger.info(f"Using LiteLLM Gateway at {self.api_base} with model {self.model}")

    async def extract_entities(
        self,
        user_text: str,
        files: Optional[List[str]] = None,
        diff: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        context: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract structured entities from user text using LLM.

        Args:
            user_text: The user's message/request
            files: Optional list of file paths involved
            diff: Optional code diff
            symbols: Optional list of code symbols
            context: Optional additional context

        Returns:
            ExtractionResult with extracted entities
        """
        logger.info(f"Extracting entities from user text: {user_text[:100]}...")

        # Build the prompt
        system_prompt, user_prompt = get_extractor_prompt(
            user_text=user_text,
            files=files,
            diff=diff,
            symbols=symbols,
            context=context,
        )

        try:
            # Build kwargs for litellm
            llm_kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": self.settings.llm_temperature,
                "max_tokens": self.settings.llm_max_tokens,
                "response_format": {"type": "json_object"},
            }
            
            # Add gateway config if using LiteLLM Gateway
            if self.api_base:
                llm_kwargs["api_base"] = self.api_base
                llm_kwargs["api_key"] = self.api_key
            
            response = await litellm.acompletion(**llm_kwargs)

            content = response.choices[0].message.content
            if not content:
                logger.warning("Empty response from LLM")
                return ExtractionResult()

            # Parse JSON response
            data = json.loads(content)
            logger.debug(f"Extracted data: {json.dumps(data, indent=2)}")

            # Validate and convert to pydantic models
            return self._parse_extraction_result(data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return ExtractionResult(confidence=0.0)
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            raise

    async def link_entities(
        self,
        extraction: ExtractionResult,
        existing_goals: List[Dict[str, Any]],
        existing_preferences: List[Dict[str, Any]],
        recent_interactions: List[Dict[str, Any]],
    ) -> LinkingResult:
        """
        Analyze extraction results and suggest links/merges with existing entities.

        Args:
            extraction: The extraction result to link
            existing_goals: List of existing goals in the graph
            existing_preferences: List of existing preferences
            recent_interactions: Recent interactions for context

        Returns:
            LinkingResult with merge and relationship suggestions
        """
        logger.info("Linking extracted entities with existing graph...")

        system_prompt, user_prompt = get_linker_prompt(
            extraction=extraction,
            existing_goals=existing_goals,
            existing_preferences=existing_preferences,
            recent_interactions=recent_interactions,
        )

        try:
            # Build kwargs for litellm
            llm_kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,  # Lower temperature for more deterministic linking
                "max_tokens": 2048,
                "response_format": {"type": "json_object"},
            }
            
            # Add gateway config if using LiteLLM Gateway
            if self.api_base:
                llm_kwargs["api_base"] = self.api_base
                llm_kwargs["api_key"] = self.api_key
            
            response = await litellm.acompletion(**llm_kwargs)

            content = response.choices[0].message.content
            if not content:
                logger.warning("Empty response from LLM for linking")
                return LinkingResult()

            data = json.loads(content)
            return self._parse_linking_result(data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse linking response as JSON: {e}")
            return LinkingResult()
        except Exception as e:
            logger.error(f"LLM linking failed: {e}")
            raise

    def _parse_extraction_result(self, data: Dict[str, Any]) -> ExtractionResult:
        """Parse raw JSON into ExtractionResult."""
        try:
            goals = [
                GoalExtract(**g) for g in data.get("goals", [])
            ]
            constraints = [
                ConstraintExtract(**c) for c in data.get("constraints", [])
            ]
            preferences = [
                PreferenceExtract(**p) for p in data.get("preferences", [])
            ]
            pain_points = [
                PainPointExtract(**pp) for pp in data.get("pain_points", [])
            ]
            strategies = [
                StrategyExtract(**s) for s in data.get("strategies", [])
            ]
            acceptance_criteria = [
                AcceptanceCriteriaExtract(**ac) for ac in data.get("acceptance_criteria", [])
            ]
            code_references = [
                CodeReference(**cr) for cr in data.get("code_references", [])
            ]
            next_actions = data.get("next_actions", [])
            confidence = data.get("confidence", 0.8)

            return ExtractionResult(
                goals=goals,
                constraints=constraints,
                preferences=preferences,
                pain_points=pain_points,
                strategies=strategies,
                acceptance_criteria=acceptance_criteria,
                code_references=code_references,
                next_actions=next_actions,
                confidence=confidence,
            )
        except ValidationError as e:
            logger.warning(f"Validation error parsing extraction: {e}")
            return ExtractionResult(confidence=0.5)

    def _parse_linking_result(self, data: Dict[str, Any]) -> LinkingResult:
        """Parse raw JSON into LinkingResult."""
        try:
            merge_suggestions = [
                MergeSuggestion(**ms) for ms in data.get("merge_suggestions", [])
            ]
            relationships = [
                RelationshipSuggestion(**r) for r in data.get("relationships", [])
            ]

            return LinkingResult(
                merge_suggestions=merge_suggestions,
                relationships=relationships,
            )
        except ValidationError as e:
            logger.warning(f"Validation error parsing linking: {e}")
            return LinkingResult()


# Singleton instance
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get or create the LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
