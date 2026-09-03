"""
Tests for Life & Work Cognitive Memory components:
- Entity extraction of Decisions, Commitments, Meetings, and Research Insights
- MemoryConsolidator briefing and compaction
- PrivacyShield sanitization
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from kg_mcp.life.analysis_schema import (
    LifeEventAnalysis,
    DecisionItem,
    CommitmentItem,
    ResearchInsightItem,
    MeetingDetails,
    EventCandidate,
)
from kg_mcp.llm.entity_extractor import extract_entities_from_analysis
from kg_mcp.services.consolidator import MemoryConsolidator
from kg_mcp.services.privacy_shield import PrivacyShield


@pytest.mark.asyncio
async def test_extract_decision_and_commitment():
    mock_repo = MagicMock()
    mock_repo.client.execute_query = AsyncMock(return_value=[])
    mock_repo.link_event_to_app = AsyncMock()

    analysis = LifeEventAnalysis(
        ts="2026-09-03T08:00:00Z",
        active_app="Mail",
        window_title="Re: Preventivo Cloud - Marco Rossi",
        decisions=[
            DecisionItem(
                verdict="APPROVED",
                title="Approvazione Preventivo Cloud",
                rationale="L'utente ha accettato la proposta economica",
                subject="Preventivo Cloud",
                target_person="Marco Rossi",
            )
        ],
        commitments=[
            CommitmentItem(
                debtor="user",
                creditor="Marco Rossi",
                task_description="Inviare contratto firmato",
                due_date_iso="2026-09-05",
                status="open",
            )
        ],
    )

    created = await extract_entities_from_analysis(
        mock_repo, "test-proj", "event-1", analysis
    )

    assert created["decisions"] == 1
    assert created["commitments"] == 1
    assert mock_repo.client.execute_query.await_count >= 2


@pytest.mark.asyncio
async def test_extract_meeting_and_insights():
    mock_repo = MagicMock()
    mock_repo.client.execute_query = AsyncMock(return_value=[])
    mock_repo.link_event_to_app = AsyncMock()

    analysis = LifeEventAnalysis(
        ts="2026-09-03T09:00:00Z",
        active_app="Google Meet",
        window_title="Meet - Sync Architettura",
        meeting_details=MeetingDetails(
            title="Sync Architettura",
            participants=["Alice", "Bob"],
            duration="30m",
        ),
        research_insights=[
            ResearchInsightItem(
                topic="Neo4j Vector Search",
                takeaway="HNSW index enables hybrid semantic and graph search",
                source_url_or_doc="https://neo4j.com/docs",
                relevance_score=0.9,
            )
        ],
    )

    created = await extract_entities_from_analysis(
        mock_repo, "test-proj", "event-2", analysis
    )

    assert created["meetings"] == 1
    assert created["research_insights"] == 1


@pytest.mark.asyncio
async def test_daily_briefing_generation():
    mock_repo = MagicMock()
    mock_repo.client.execute_query = AsyncMock(side_effect=[
        # decisions
        [{"title": "Preventivo Approvato", "verdict": "APPROVED", "rationale": "Ok", "counterparty": "Marco", "artifact_title": "Preventivo"}],
        # commitments
        [{"title": "Inviare contratto", "task": "Inviare contratto firmato", "due_date": "2026-09-05", "status": "open", "debtor": "user", "creditor_name": "Marco", "debtor_name": None}],
        # meetings
        [{"title": "Sync Architettura", "duration": "30m", "participants": ["Alice", "Bob"], "topics": ["Neo4j"]}],
        # insights
        [{"topic": "Vector Index", "takeaway": "HNSW index", "source": "docs"}],
    ])

    consolidator = MemoryConsolidator(project_id="test-proj")
    consolidator.repo = mock_repo

    briefing = await consolidator.generate_daily_briefing(target_date="2026-09-03")

    assert briefing["date"] == "2026-09-03"
    assert briefing["summary_counts"]["decisions_count"] == 1
    assert briefing["summary_counts"]["commitments_count"] == 1
    assert briefing["summary_counts"]["meetings_count"] == 1
    assert briefing["summary_counts"]["research_insights_count"] == 1
    assert briefing["decisions"][0]["title"] == "Preventivo Approvato"


def test_privacy_shield_comprehensive():
    # Credit card (Visa format)
    cc_text = "Ecco il numero della carta 4532 0151 1283 0366 per il pagamento"
    masked = PrivacyShield.sanitize_text(cc_text)
    assert "[REDACTED_PAYMENT_CARD]" in masked

    # IBAN
    iban_text = "Bonifico su IT60X0542811101000000123456"
    assert "[REDACTED_IBAN]" in PrivacyShield.sanitize_text(iban_text)

    # API key
    key_text = "Usa sk-abcdef1234567890abcdef123456"
    assert "[REDACTED_API_KEY]" in PrivacyShield.sanitize_text(key_text)

    # Context checks
    assert PrivacyShield.is_sensitive_context("1Password", "") is True
    assert PrivacyShield.is_sensitive_context("Chrome", "Google Chrome - Private Browsing") is True
    assert PrivacyShield.is_sensitive_context("Slack", "#general") is False
