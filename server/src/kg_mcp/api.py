"""Local HTTP API used by Neural Memory capture clients."""

from __future__ import annotations

import hmac
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from kg_mcp import __version__
from kg_mcp.config import get_settings
from kg_mcp.kg.repo import KGRepository, get_repository
from kg_mcp.life.analysis_schema import InteractionBundleIn
from kg_mcp.services.privacy_shield import PrivacyShield
from kg_mcp.utils import serialize_response

logger = logging.getLogger(__name__)


class EventIn(BaseModel):
    """A single opt-in activity event from a trusted local client."""

    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(default="default", min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=64)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
    text_content: str | None = None
    screenshot_base64: str | None = None

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_capture_payload(self) -> "EventIn":
        settings = get_settings()
        if self.text_content and len(self.text_content) > settings.max_text_chars:
            raise ValueError(f"text_content exceeds {settings.max_text_chars} characters")
        if (
            self.screenshot_base64
            and len(self.screenshot_base64) > settings.max_screenshot_base64_chars
        ):
            raise ValueError("screenshot_base64 exceeds the configured size limit")
        return self


class SliceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(default="default", min_length=1, max_length=128)
    summary: str | None = Field(default=None, max_length=8_000)
    event_ids: list[str] = Field(default_factory=list, max_length=1_000)
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def validate_range(self) -> "SliceIn":
        if self.end_time < self.start_time:
            raise ValueError("end_time must not be before start_time")
        return self


class DeepSearchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1, max_length=2_000)
    project_id: str = Field(default="default", min_length=1, max_length=128)
    limit: int = Field(default=5, ge=1, le=50)


def require_token(authorization: str | None = Header(default=None)) -> None:
    """Require the bootstrap-generated bearer token for private API routes."""
    configured = get_settings().kg_mcp_token
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server token is not configured. Run ./scripts/bootstrap.sh.",
        )
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not supplied:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required"
        )
    if not hmac.compare_digest(supplied, configured):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bearer token")


async def _process_screenshot(repo: KGRepository, payload: EventIn, event_id: str) -> None:
    from kg_mcp.llm.entity_extractor import (
        extract_entities_from_analysis,
        update_raw_event_with_analysis,
    )
    from kg_mcp.llm.vision_analyzer import analyze_screenshot

    try:
        analysis = await analyze_screenshot(
            screenshot_base64=payload.screenshot_base64 or "",
            app=str(payload.data.get("app", "Unknown")),
            window=str(payload.data.get("window", "")),
        )
        await update_raw_event_with_analysis(repo, event_id, analysis)
        if analysis.primary_event_type() != "IDLE" or analysis.concepts:
            await extract_entities_from_analysis(repo, payload.project_id, event_id, analysis)
    except Exception:
        logger.exception("Optional screenshot enrichment failed for event %s", event_id)


async def _process_text(repo: KGRepository, payload: EventIn, event_id: str) -> None:
    from kg_mcp.llm.entity_extractor import (
        extract_entities_from_analysis,
        update_raw_event_with_analysis,
    )
    from kg_mcp.llm.vision_analyzer import analyze_text_content

    try:
        analysis = await analyze_text_content(
            text_content=payload.text_content or "", app=str(payload.data.get("app", "Unknown"))
        )
        await update_raw_event_with_analysis(repo, event_id, analysis)
        if analysis.primary_event_type() != "IDLE" or analysis.concepts:
            await extract_entities_from_analysis(repo, payload.project_id, event_id, analysis)
    except Exception:
        logger.exception("Optional text enrichment failed for event %s", event_id)


async def _process_bundle(repo: KGRepository, payload: InteractionBundleIn, event_id: str) -> None:
    from kg_mcp.llm.entity_extractor import (
        extract_entities_from_analysis,
        update_raw_event_with_analysis,
    )
    from kg_mcp.llm.vision_analyzer import analyze_interaction_bundle

    try:
        analysis = await analyze_interaction_bundle(
            app=payload.app,
            window=payload.window_title,
            keystrokes_typed=payload.keystrokes_typed or "",
            mouse_actions=payload.mouse_actions or [],
            trigger_reason=payload.trigger_reason or "window_switch",
            screenshot_base64=payload.screenshot_base64,
        )
        await update_raw_event_with_analysis(repo, event_id, analysis)
        await extract_entities_from_analysis(repo, payload.project_id, event_id, analysis)
    except Exception:
        logger.exception("Bundle enrichment failed for event %s", event_id)


def create_api_app(
    repository_factory: Callable[[], KGRepository] = get_repository,
    *,
    lifespan=None,
) -> FastAPI:
    """Build the API separately so it can be tested without external services."""
    app = FastAPI(
        title="Neural Memory API",
        version=__version__,
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def enforce_request_size(request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > get_settings().max_request_bytes:
                    return JSONResponse(
                        status_code=413, content={"detail": "Request body is too large"}
                    )
            except ValueError:
                return JSONResponse(
                    status_code=400, content={"detail": "Invalid Content-Length header"}
                )
        return await call_next(request)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "neural-memory", "version": __version__}

    @app.post("/api/ingest/event", dependencies=[Depends(require_token)])
    async def ingest_event(payload: EventIn, background: BackgroundTasks) -> dict[str, Any]:
        repo = repository_factory()
        screenshot_hash = None
        duplicate_of = None
        is_duplicate = False
        has_screenshot = bool(payload.screenshot_base64) and payload.data.get("has_screenshot") in (
            True,
            "true",
        )

        if has_screenshot:
            from kg_mcp.image_hash import dhash_from_base64, hamming_distance

            try:
                screenshot_hash = dhash_from_base64(payload.screenshot_base64 or "")
                if not screenshot_hash:
                    raise ValueError("Screenshot is not a supported image")
                last_event = await repo.get_last_screenshot_event(payload.project_id)
                if screenshot_hash and last_event and last_event.get("screenshot_hash"):
                    distance = hamming_distance(screenshot_hash, last_event["screenshot_hash"])
                    last_timestamp = last_event.get("timestamp")
                    if hasattr(last_timestamp, "to_native"):
                        last_timestamp = last_timestamp.to_native()
                    elif isinstance(last_timestamp, str):
                        last_timestamp = datetime.fromisoformat(
                            last_timestamp.replace("Z", "+00:00")
                        )
                    if isinstance(last_timestamp, datetime):
                        if last_timestamp.tzinfo is None:
                            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
                        seconds = abs(
                            (
                                payload.timestamp - last_timestamp.astimezone(timezone.utc)
                            ).total_seconds()
                        )
                        settings = get_settings()
                        if (
                            distance <= settings.screenshot_dedupe_hamming
                            and seconds <= settings.screenshot_dedupe_window_seconds
                        ):
                            is_duplicate = True
                            duplicate_of = last_event.get("id")
            except (ValueError, TypeError):
                raise HTTPException(status_code=422, detail="Invalid screenshot payload") from None

        try:
            result = await repo.upsert_raw_event(
                project_id=payload.project_id,
                event_type=payload.event_type,
                timestamp=payload.timestamp,
                data=payload.data,
                text_content=payload.text_content,
                screenshot_hash=screenshot_hash,
                is_duplicate=is_duplicate,
                duplicate_of=duplicate_of,
            )
        except Exception:
            logger.exception("Event ingestion failed")
            raise HTTPException(status_code=503, detail="Memory store is unavailable") from None

        event_id = str(result.get("id", ""))
        if get_settings().llm_enabled:
            if has_screenshot and not is_duplicate:
                background.add_task(_process_screenshot, repo, payload, event_id)
            elif (
                payload.event_type == "keystroke_buffer"
                and payload.text_content
                and len(payload.text_content.strip()) >= 2
            ):
                background.add_task(_process_text, repo, payload, event_id)
        return serialize_response(result)

    @app.post("/api/ingest/bundle", dependencies=[Depends(require_token)])
    async def ingest_bundle(
        payload: InteractionBundleIn,
        background: BackgroundTasks,
    ) -> dict[str, Any]:
        if PrivacyShield.is_sensitive_context(payload.app, payload.window_title):
            return {"status": "ignored", "reason": "sensitive_private_context"}

        repo = repository_factory()
        sanitized_text = PrivacyShield.sanitize_text(payload.keystrokes_typed or "")

        data = {
            "app": payload.app,
            "window": payload.window_title,
            "mouse_actions": payload.mouse_actions,
            "trigger_reason": payload.trigger_reason,
            "has_screenshot": bool(payload.screenshot_base64),
        }

        try:
            result = await repo.upsert_raw_event(
                project_id=payload.project_id,
                event_type="interaction_bundle",
                timestamp=payload.timestamp or datetime.now(timezone.utc),
                data=data,
                text_content=sanitized_text,
                is_duplicate=False,
            )
        except Exception:
            logger.exception("Bundle ingestion failed")
            raise HTTPException(status_code=503, detail="Memory store is unavailable") from None

        event_id = str(result.get("id", ""))
        if get_settings().llm_enabled:
            payload.keystrokes_typed = sanitized_text
            background.add_task(_process_bundle, repo, payload, event_id)

        return serialize_response(result)

    @app.post("/api/ingest/slice", dependencies=[Depends(require_token)])
    async def ingest_slice(payload: SliceIn) -> dict[str, Any]:
        try:
            res = await repository_factory().upsert_activity_slice(
                project_id=payload.project_id,
                start_time=payload.start_time,
                end_time=payload.end_time,
                summary=payload.summary,
                event_ids=payload.event_ids,
            )
            return serialize_response(res)
        except Exception:
            logger.exception("Slice ingestion failed")
            raise HTTPException(status_code=503, detail="Memory store is unavailable") from None

    @app.post("/api/search/deep", dependencies=[Depends(require_token)])
    async def deep_search(payload: DeepSearchIn) -> Any:
        from kg_mcp.services.deep_search import DeepSearchService

        try:
            service = DeepSearchService(project_id=payload.project_id)
            return serialize_response(
                await service.search(query=payload.query, limit=payload.limit)
            )
        except Exception:
            logger.exception("Deep search failed")
            raise HTTPException(
                status_code=503, detail="Search is temporarily unavailable"
            ) from None

    @app.post("/api/memory/consolidate", dependencies=[Depends(require_token)])
    async def consolidate_memory(
        project_id: str = "default", retention_days: int = 2, run_dream: bool = False
    ) -> dict[str, Any]:
        from kg_mcp.services.consolidator import MemoryConsolidator

        try:
            consolidator = MemoryConsolidator(project_id=project_id)
            pruned = await consolidator.prune_ephemeral_events(retention_days=retention_days)
            deduped = await consolidator.deduplicate_topics()
            result = {"status": "ok", "pruned_events": pruned, "deduped_topics": deduped}
            if run_dream:
                result["dream"] = await consolidator.run_dream_cycle()
            return result
        except Exception:
            logger.exception("Memory consolidation failed")
            raise HTTPException(status_code=500, detail="Consolidation failed") from None

    @app.post("/api/memory/dream", dependencies=[Depends(require_token)])
    async def run_dream_cycle(project_id: str = "default") -> dict[str, Any]:
        from kg_mcp.services.consolidator import MemoryConsolidator

        try:
            consolidator = MemoryConsolidator(project_id=project_id)
            return await consolidator.run_dream_cycle()
        except Exception:
            logger.exception("Dream cycle failed")
            raise HTTPException(status_code=500, detail="Dream cycle failed") from None

    @app.get("/api/memory/reflections", dependencies=[Depends(require_token)])
    async def get_reflections(
        project_id: str = "default",
        category: str | None = None,
        topic: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        from kg_mcp.services.consolidator import MemoryConsolidator

        try:
            consolidator = MemoryConsolidator(project_id=project_id)
            return await consolidator.recall_reflections(
                category=category, topic=topic, limit=limit
            )
        except Exception:
            logger.exception("Recalling reflections failed")
            raise HTTPException(status_code=500, detail="Recalling reflections failed") from None

    @app.get("/api/memory/briefing", dependencies=[Depends(require_token)])
    async def get_briefing(project_id: str = "default", date: str | None = None) -> dict[str, Any]:
        from kg_mcp.services.consolidator import MemoryConsolidator

        try:
            consolidator = MemoryConsolidator(project_id=project_id)
            return await consolidator.generate_daily_briefing(target_date=date)
        except Exception:
            logger.exception("Daily briefing generation failed")
            raise HTTPException(status_code=500, detail="Briefing generation failed") from None

    @app.get("/api/config", dependencies=[Depends(require_token)])
    async def get_config() -> dict[str, Any]:
        settings = get_settings()
        return serialize_response({
            "llm_enabled": settings.llm_enabled,
            "llm_mode": settings.llm_mode,
            "litellm_model": settings.litellm_model,
            "gemini_model": settings.gemini_model,
            "mcp_port": settings.mcp_port,
        })

    return app
