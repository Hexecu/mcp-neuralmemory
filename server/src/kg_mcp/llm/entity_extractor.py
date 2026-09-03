"""
Entity Extractor - Creates Neo4j entities from life-event analysis results.
"""
import json
import logging
from typing import Dict, Any
from uuid import uuid4

from kg_mcp.life.analysis_schema import LifeEventAnalysis
from kg_mcp.life.artifact_canonicalizer import canonicalize_artifact
from kg_mcp.llm.client import get_llm_client

logger = logging.getLogger(__name__)


def _analysis_summary(analysis: LifeEventAnalysis) -> str:
    if analysis.artifact.title:
        return f"{analysis.active_app}: {analysis.artifact.title}"
    top_concepts = analysis.primary_concepts(limit=3)
    if top_concepts:
        return f"{analysis.active_app}: {', '.join(top_concepts)}"
    return f"{analysis.active_app} activity"


async def extract_entities_from_analysis(
    repo,
    project_id: str,
    raw_event_id: str,
    analysis: LifeEventAnalysis
) -> Dict[str, int]:
    """
    Create Neo4j entities from life-event analysis.
    """
    created = {
        "artifacts": 0,
        "concepts": 0,
        "snippets": 0,
        "entities": 0,
        "action_items": 0,
        "decisions": 0,
    }

    llm_client = get_llm_client()

    # Artifact handling
    artifact_info = canonicalize_artifact(
        analysis.artifact.model_dump(),
        app=analysis.active_app,
        window_title=analysis.window_title,
    )
    artifact_id = None
    if artifact_info.get("canonical_id"):
        embedding = None
        try:
            content = f"{artifact_info.get('title', '')} {artifact_info.get('url_or_path', '')}".strip()
            if content:
                embedding = await llm_client.embed(content)
        except Exception:
            embedding = None
        artifact = await repo.upsert_artifact(
            project_id=project_id,
            canonical_id=artifact_info.get("canonical_id"),
            artifact_type=artifact_info.get("type", "unknown"),
            title=artifact_info.get("title"),
            url_or_path=artifact_info.get("url_or_path"),
            owner_org=artifact_info.get("owner_org"),
            embedding=embedding,
        )
        artifact_id = artifact.get("id")
        created["artifacts"] += 1
        await repo.link_event_to_artifact(raw_event_id, artifact_id)

    # Link event to app
    if analysis.active_app:
        await repo.link_event_to_app(raw_event_id, analysis.active_app)

    # Concepts
    for concept in analysis.concepts:
        if not concept.label:
            continue
        await repo.link_event_to_topic(raw_event_id, concept.label, concept.confidence)
        created["concepts"] += 1

    # Entities (Person/Organization)
    for entity in analysis.entities:
        if not entity.value:
            continue
        kind = entity.kind.lower()
        if kind in ("person", "organization"):
            try:
                await repo.upsert_entity(project_id, entity.value, "Person" if kind == "person" else "Organization")
                created["entities"] += 1
            except Exception as e:
                logger.debug(f"Entity upsert skipped: {e}")

    # Snippets
    for snippet in analysis.visible_text_snippets:
        if not snippet.text.strip():
            continue
        if snippet.confidence < 0.5:
            continue
        embedding = None
        try:
            embedding = await llm_client.embed(snippet.text.strip())
        except Exception:
            embedding = None
        await repo.upsert_snippet(
            project_id=project_id,
            text=snippet.text.strip(),
            confidence=snippet.confidence,
            embedding=embedding,
            source_event_id=raw_event_id,
            artifact_id=artifact_id,
        )
        created["snippets"] += 1

    # Action items & decisions from event candidates
    event_types = {c.type for c in analysis.event_candidates if c.confidence >= 0.6}
    if "TODO_FOUND" in event_types or "ERROR_BLOCKER" in event_types:
        title = None
        for snippet in analysis.visible_text_snippets:
            text = snippet.text.lower()
            if "todo" in text or "follow" in text or "fix" in text:
                title = snippet.text[:120]
                break
        if not title:
            title = _analysis_summary(analysis)

        status = "open"
        if "ERROR_BLOCKER" in event_types:
            title = f"Blocker: {title}"
        await repo.upsert_action_item(
            project_id=project_id,
            title=title,
            status=status,
            priority="high" if "ERROR_BLOCKER" in event_types else "medium",
            score=1.0,
            source_id=raw_event_id,
        )
        created["action_items"] += 1

    if "DECISION" in event_types:
        decision_text = None
        for snippet in analysis.visible_text_snippets:
            if len(snippet.text) > 10:
                decision_text = snippet.text
                break
        if not decision_text:
            decision_text = _analysis_summary(analysis)
        await _create_decision(repo, project_id, raw_event_id, decision_text)
        created["decisions"] += 1

    return created


async def _create_decision(
    repo,
    project_id: str,
    raw_event_id: str,
    text: str,
) -> None:
    decision_id = str(uuid4())
    query = """
    MATCH (p:Project {id: $project_id})
    MATCH (re:RawEvent {id: $event_id})
    CREATE (d:Decision {
        id: $decision_id,
        title: $title,
        decision: $decision,
        decided_at: datetime(),
        project_id: $project_id,
        created_at: datetime()
    })
    MERGE (d)-[:IN_PROJECT]->(p)
    MERGE (d)-[:DERIVED_FROM]->(re)
    """
    await repo.client.execute_query(
        query,
        {
            "project_id": project_id,
            "event_id": raw_event_id,
            "decision_id": decision_id,
            "title": text[:120],
            "decision": text,
        }
    )


async def update_raw_event_with_analysis(
    repo,
    raw_event_id: str,
    analysis: LifeEventAnalysis
) -> None:
    """Update the RawEvent with analysis details."""
    artifact_info = canonicalize_artifact(
        analysis.artifact.model_dump(),
        app=analysis.active_app,
        window_title=analysis.window_title,
    )
    primary_event = analysis.primary_event_type()
    concept_labels = [c.label for c in analysis.concepts if c.label]
    confidence = 0.0
    if analysis.event_candidates:
        confidence = max(c.confidence for c in analysis.event_candidates)

    is_noise = primary_event == "IDLE" and not concept_labels and not artifact_info.get("canonical_id")

    summary = _analysis_summary(analysis)

    query = """
    MATCH (r:RawEvent {id: $event_id})
    SET r.analysis_json = $analysis_json,
        r.analysis_summary = $summary,
        r.analysis_confidence = $confidence,
        r.is_noise = $is_noise,
        r.normalized_type = $normalized_type,
        r.artifact_canonical_id = $artifact_canonical_id,
        r.artifact_title = $artifact_title,
        r.artifact_type = $artifact_type,
        r.artifact_url = $artifact_url,
        r.concepts = $concepts,
        r.app = COALESCE(r.app, $active_app),
        r.window_title = COALESCE(r.window_title, $window_title),
        r.blocker = $blocker,
        r.urgency = $urgency,
        r.analyzed_at = datetime()
    """

    await repo.client.execute_query(
        query,
        {
            "event_id": raw_event_id,
            "analysis_json": json.dumps(analysis.model_dump()),
            "summary": summary,
            "confidence": confidence,
            "is_noise": is_noise,
            "normalized_type": primary_event,
            "artifact_canonical_id": artifact_info.get("canonical_id"),
            "artifact_title": artifact_info.get("title"),
            "artifact_type": artifact_info.get("type"),
            "artifact_url": artifact_info.get("url_or_path"),
            "concepts": concept_labels,
            "active_app": analysis.active_app,
            "window_title": analysis.window_title,
            "blocker": analysis.sentiment_or_state.blocker,
            "urgency": analysis.sentiment_or_state.urgency,
        }
    )
