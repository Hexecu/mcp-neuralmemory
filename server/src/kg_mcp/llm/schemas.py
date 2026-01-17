"""
Pydantic schemas for LLM input/output validation.
These define the structured format for entity extraction and linking.
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# Extraction Schemas
# =============================================================================


class GoalExtract(BaseModel):
    """Extracted goal from user text."""

    title: str = Field(..., description="Short title of the goal")
    description: Optional[str] = Field(None, description="Detailed description")
    priority: int = Field(default=2, ge=1, le=5, description="Priority 1-5 (1=highest)")
    status: str = Field(default="active", description="Status: active, paused, done")
    parent_goal_title: Optional[str] = Field(
        None, description="Title of parent goal if this is a subgoal"
    )


class ConstraintExtract(BaseModel):
    """Extracted constraint from user text."""

    type: str = Field(..., description="Constraint type: budget, stack, style, performance, time")
    description: str = Field(..., description="Description of the constraint")
    severity: str = Field(default="must", description="Severity: must, should, nice_to_have")


class PreferenceExtract(BaseModel):
    """Extracted preference from user text."""

    category: str = Field(
        ...,
        description="Category: coding_style, architecture, testing, tools, output_format",
    )
    preference: str = Field(..., description="The preference itself")
    strength: str = Field(default="prefer", description="Strength: prefer, avoid, require")


class PainPointExtract(BaseModel):
    """Extracted pain point from user text."""

    description: str = Field(..., description="Description of the pain point")
    severity: str = Field(default="medium", description="Severity: low, medium, high, critical")
    related_goal: Optional[str] = Field(None, description="Related goal title if any")


class StrategyExtract(BaseModel):
    """Extracted strategy from user text."""

    title: str = Field(..., description="Short title of the strategy")
    approach: str = Field(..., description="Description of the approach")
    rationale: Optional[str] = Field(None, description="Why this strategy was chosen")
    related_goal: Optional[str] = Field(None, description="Related goal title if any")


class AcceptanceCriteriaExtract(BaseModel):
    """Extracted acceptance criteria from user text."""

    criterion: str = Field(..., description="The acceptance criterion")
    related_goal: Optional[str] = Field(None, description="Related goal title")
    testable: bool = Field(default=True, description="Whether it's testable")


class CodeReference(BaseModel):
    """Reference to code in the message."""

    path: str = Field(..., description="File path")
    symbol: Optional[str] = Field(None, description="Symbol name (function/class)")
    start_line: Optional[int] = Field(None, description="Start line number")
    end_line: Optional[int] = Field(None, description="End line number")
    action: str = Field(
        default="reference", description="Action: reference, create, modify, delete"
    )


class ExtractionResult(BaseModel):
    """Complete result of entity extraction from user text."""

    goals: List[GoalExtract] = Field(default_factory=list)
    constraints: List[ConstraintExtract] = Field(default_factory=list)
    preferences: List[PreferenceExtract] = Field(default_factory=list)
    pain_points: List[PainPointExtract] = Field(default_factory=list)
    strategies: List[StrategyExtract] = Field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriteriaExtract] = Field(default_factory=list)
    code_references: List[CodeReference] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


# =============================================================================
# Linking Schemas
# =============================================================================


class MergeSuggestion(BaseModel):
    """Suggestion to merge a new entity with an existing one."""

    new_entity_type: str = Field(..., description="Type of the new entity")
    new_entity_title: str = Field(..., description="Title of the new entity")
    existing_entity_id: str = Field(..., description="ID of the existing entity to merge with")
    existing_entity_title: str = Field(..., description="Title of existing entity")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    reason: str = Field(..., description="Why these should be merged")


class RelationshipSuggestion(BaseModel):
    """Suggestion for a new relationship between entities."""

    source_type: str = Field(..., description="Type of source entity")
    source_id: Optional[str] = Field(None, description="ID of source entity (if existing)")
    source_title: str = Field(..., description="Title of source entity")
    relationship_type: str = Field(..., description="Type of relationship (e.g., IMPLEMENTED_BY)")
    target_type: str = Field(..., description="Type of target entity")
    target_id: Optional[str] = Field(None, description="ID of target entity (if existing)")
    target_title: str = Field(..., description="Title of target entity")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class LinkingResult(BaseModel):
    """Result of entity linking analysis."""

    merge_suggestions: List[MergeSuggestion] = Field(default_factory=list)
    relationships: List[RelationshipSuggestion] = Field(default_factory=list)


# =============================================================================
# Graph Node Schemas (for Neo4j)
# =============================================================================


class BaseNode(BaseModel):
    """Base class for all graph nodes."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InteractionNode(BaseNode):
    """Represents a user interaction/request."""

    user_text: str
    assistant_text: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    project_id: str


class GoalNode(BaseNode):
    """Represents a goal or objective."""

    title: str
    description: Optional[str] = None
    status: str = "active"
    priority: int = 2
    project_id: str


class ConstraintNode(BaseNode):
    """Represents a constraint."""

    type: str
    description: str
    severity: str = "must"
    project_id: str


class PreferenceNode(BaseNode):
    """Represents a user preference."""

    category: str
    preference: str
    strength: str = "prefer"
    user_id: str


class PainPointNode(BaseNode):
    """Represents a pain point."""

    description: str
    severity: str = "medium"
    resolved: bool = False
    project_id: str


class StrategyNode(BaseNode):
    """Represents a strategy or approach."""

    title: str
    approach: str
    rationale: Optional[str] = None
    project_id: str


class DecisionNode(BaseNode):
    """Represents an ADR-lite decision."""

    title: str
    decision: str
    rationale: str
    alternatives: List[str] = Field(default_factory=list)
    project_id: str


class CodeArtifactNode(BaseNode):
    """Represents a code artifact (file, function, class, snippet)."""

    path: str
    language: Optional[str] = None
    kind: str = "file"  # file, function, class, snippet
    git_commit: Optional[str] = None
    content_hash: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    project_id: str


class SymbolNode(BaseNode):
    """Represents a code symbol (function, class, method)."""

    fqn: str  # fully qualified name
    name: str
    kind: str  # function, class, method, variable
    signature: Optional[str] = None
    artifact_id: str


class TestCaseNode(BaseNode):
    """Represents a test case."""

    name: str
    kind: str = "unit"  # unit, integration, e2e, manual
    path: Optional[str] = None
    status: str = "pending"  # pending, passed, failed
    project_id: str
