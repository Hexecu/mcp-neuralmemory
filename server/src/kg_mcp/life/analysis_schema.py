from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator

from kg_mcp.life.event_taxonomy import EVENT_TYPES


class ArtifactInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str = Field(default="unknown")
    canonical_id: str = Field(default="")
    title: str = Field(default="")
    url_or_path: str = Field(default="")
    owner_org: Optional[str] = Field(default=None)

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

    text: str = Field(default="")
    source: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class EntityItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: str = Field(default="unknown")
    value: str = Field(default="")
    role: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ConceptItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str = Field(default="")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SentimentState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    blocker: bool = Field(default=False)
    urgency: float = Field(default=0.0, ge=0.0, le=1.0)
    activity_type: str = Field(default="idle")


class MeetingDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(default="")
    participants: List[str] = Field(default_factory=list)
    duration: str = Field(default="")
    is_recording: bool = Field(default=False)


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
