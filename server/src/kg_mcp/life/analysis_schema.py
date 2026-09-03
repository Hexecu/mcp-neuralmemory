from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

from kg_mcp.life.event_taxonomy import EVENT_TYPES


class ArtifactInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str = Field(default="unknown")
    canonical_id: Optional[str] = Field(default="")
    title: Optional[str] = Field(default="")
    url_or_path: Optional[str] = Field(default="")
    owner_org: Optional[str] = Field(default=None)

    @field_validator("canonical_id", "title", "url_or_path", mode="before")
    @classmethod
    def ensure_string_fields(cls, value: Optional[str]) -> str:
        return value or ""

    @field_validator("type")
    @classmethod
    def normalize_type(cls, value: str) -> str:
        value = (value or "unknown").strip().lower()
        allowed = {"web", "doc", "email", "ticket", "chat", "sheet", "ide", "meeting", "calendar", "unknown"}
        return value if value in allowed else "unknown"


class EventCandidate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str = Field(default="IDLE")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("type")
    @classmethod
    def normalize_type(cls, value: str) -> str:
        value = (value or "IDLE").strip().upper()
        return value if value in EVENT_TYPES else "IDLE"


class TextSnippet(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: Optional[str] = Field(default="")
    source: Optional[str] = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class EntityItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Optional[str] = Field(default="unknown")
    value: Optional[str] = Field(default="")
    role: Optional[str] = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ConceptItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: Optional[str] = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SentimentState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    blocker: bool = Field(default=False)
    urgency: float = Field(default=0.0, ge=0.0, le=1.0)
    activity_type: str = Field(default="idle")


class MeetingDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: Optional[str] = Field(default="")
    participants: List[str] = Field(default_factory=list)
    duration: Optional[str] = Field(default="")
    is_recording: bool = Field(default=False)


class DecisionItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    verdict: Optional[str] = Field(default="APPROVED")
    title: Optional[str] = Field(default="")
    rationale: Optional[str] = Field(default="")
    subject: Optional[str] = Field(default="")
    target_person: Optional[str] = Field(default=None)
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class CommitmentItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    debtor: Optional[str] = Field(default="user")
    creditor: Optional[str] = Field(default=None)
    task_description: Optional[str] = Field(default="")
    due_date_iso: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default="open")
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)


class ResearchInsightItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    topic: Optional[str] = Field(default="")
    takeaway: Optional[str] = Field(default="")
    source_url_or_doc: Optional[str] = Field(default=None)
    relevance_score: float = Field(default=0.8, ge=0.0, le=1.0)


class InteractionBundleIn(BaseModel):
    """A multimodal action block bundling screen state, mouse interactions, and typed text."""
    model_config = ConfigDict(extra="ignore")

    project_id: str = Field(default="default")
    timestamp: Optional[datetime] = None
    app: str = Field(default="Unknown")
    window_title: str = Field(default="")
    screenshot_base64: Optional[str] = None
    keystrokes_typed: Optional[str] = Field(default="")
    mouse_actions: List[str] = Field(default_factory=list)
    trigger_reason: str = Field(default="window_switch")


class LifeEventAnalysis(BaseModel):
    model_config = ConfigDict(extra="ignore")

    ts: str = Field(default="")
    active_app: str = Field(default="")
    window_title: str = Field(default="")
    artifact: ArtifactInfo = Field(default_factory=ArtifactInfo)
    event_candidates: List[EventCandidate] = Field(default_factory=list)
    visible_text_snippets: List[TextSnippet] = Field(default_factory=list)
    entities: List[EntityItem] = Field(default_factory=list)
    concepts: List[ConceptItem] = Field(default_factory=list)
    decisions: List[DecisionItem] = Field(default_factory=list)
    commitments: List[CommitmentItem] = Field(default_factory=list)
    research_insights: List[ResearchInsightItem] = Field(default_factory=list)
    meeting_details: Optional[MeetingDetails] = Field(default=None)
    sentiment_or_state: SentimentState = Field(default_factory=SentimentState)

    @field_validator("active_app", "window_title", mode="before")
    @classmethod
    def ensure_string(cls, value: Optional[str]) -> str:
        return value or ""

    def primary_event_type(self) -> str:
        if not self.event_candidates:
            return "IDLE"
        return max(self.event_candidates, key=lambda c: c.confidence).type

    def primary_concepts(self, limit: int = 3) -> List[str]:
        concepts = sorted(self.concepts, key=lambda c: c.confidence, reverse=True)
        return [c.label for c in concepts[:limit] if c.label]
