"""
Tests for the ingest pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from kg_mcp.kg.ingest import IngestPipeline
from kg_mcp.llm.schemas import (
    ExtractionResult,
    LinkingResult,
    GoalExtract,
    PreferenceExtract,
    ConstraintExtract,
)


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.extract_entities = AsyncMock(
        return_value=ExtractionResult(
            goals=[
                GoalExtract(
                    title="Implement feature X",
                    description="Add new feature X to the system",
                    priority=2,
                    status="active",
                )
            ],
            preferences=[
                PreferenceExtract(
                    category="coding_style",
                    preference="Use type hints everywhere",
                    strength="require",
                )
            ],
            constraints=[
                ConstraintExtract(
                    type="time",
                    description="Must be completed by Friday",
                    severity="must",
                )
            ],
            confidence=0.85,
        )
    )
    client.link_entities = AsyncMock(return_value=LinkingResult())
    return client


@pytest.fixture
def mock_repository():
    """Create a mock repository."""
    repo = MagicMock()
    repo.get_or_create_project = AsyncMock(return_value={"id": "test-project"})
    repo.create_interaction = AsyncMock(
        return_value={"id": "interaction-123", "user_text": "test"}
    )
    repo.get_all_goals = AsyncMock(return_value=[])
    repo.get_preferences = AsyncMock(return_value=[])
    repo.get_recent_interactions = AsyncMock(return_value=[])
    repo.upsert_goal = AsyncMock(return_value={"id": "goal-123", "title": "Test Goal"})
    repo.upsert_preference = AsyncMock(return_value={"id": "pref-123"})
    repo.upsert_constraint = AsyncMock(return_value={"id": "constraint-123"})
    repo.link_interaction_to_goal = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_ingest_creates_interaction(mock_llm_client, mock_repository):
    """Test that ingest creates an interaction node."""
    with patch("kg_mcp.kg.ingest.get_llm_client", return_value=mock_llm_client):
        with patch("kg_mcp.kg.ingest.get_repository", return_value=mock_repository):
            pipeline = IngestPipeline()
            pipeline.llm = mock_llm_client
            pipeline.repo = mock_repository

            result = await pipeline.process_message(
                project_id="test-project",
                user_text="Implement feature X by Friday",
            )

            assert result["interaction_id"] == "interaction-123"
            mock_repository.create_interaction.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_extracts_goals(mock_llm_client, mock_repository):
    """Test that ingest extracts goals from user text."""
    with patch("kg_mcp.kg.ingest.get_llm_client", return_value=mock_llm_client):
        with patch("kg_mcp.kg.ingest.get_repository", return_value=mock_repository):
            pipeline = IngestPipeline()
            pipeline.llm = mock_llm_client
            pipeline.repo = mock_repository

            result = await pipeline.process_message(
                project_id="test-project",
                user_text="Implement feature X by Friday",
            )

            # Check that goals were extracted
            assert len(result["extracted"]["goals"]) == 1
            assert result["extracted"]["goals"][0]["title"] == "Implement feature X"

            # Check that goal was saved
            mock_repository.upsert_goal.assert_called()


@pytest.mark.asyncio
async def test_ingest_saves_preferences(mock_llm_client, mock_repository):
    """Test that ingest saves extracted preferences."""
    with patch("kg_mcp.kg.ingest.get_llm_client", return_value=mock_llm_client):
        with patch("kg_mcp.kg.ingest.get_repository", return_value=mock_repository):
            pipeline = IngestPipeline()
            pipeline.llm = mock_llm_client
            pipeline.repo = mock_repository

            result = await pipeline.process_message(
                project_id="test-project",
                user_text="Always use type hints",
                user_id="test-user",
            )

            assert len(result["extracted"]["preferences"]) == 1
            mock_repository.upsert_preference.assert_called()


@pytest.mark.asyncio
async def test_ingest_saves_constraints(mock_llm_client, mock_repository):
    """Test that ingest saves extracted constraints."""
    with patch("kg_mcp.kg.ingest.get_llm_client", return_value=mock_llm_client):
        with patch("kg_mcp.kg.ingest.get_repository", return_value=mock_repository):
            pipeline = IngestPipeline()
            pipeline.llm = mock_llm_client
            pipeline.repo = mock_repository

            result = await pipeline.process_message(
                project_id="test-project",
                user_text="Must be done by Friday",
            )

            assert len(result["extracted"]["constraints"]) == 1
            mock_repository.upsert_constraint.assert_called()


@pytest.mark.asyncio
async def test_ingest_links_interaction_to_goal(mock_llm_client, mock_repository):
    """Test that interaction is linked to created goal."""
    with patch("kg_mcp.kg.ingest.get_llm_client", return_value=mock_llm_client):
        with patch("kg_mcp.kg.ingest.get_repository", return_value=mock_repository):
            pipeline = IngestPipeline()
            pipeline.llm = mock_llm_client
            pipeline.repo = mock_repository

            await pipeline.process_message(
                project_id="test-project",
                user_text="Implement feature X",
            )

            mock_repository.link_interaction_to_goal.assert_called()


@pytest.mark.asyncio
async def test_ingest_returns_confidence(mock_llm_client, mock_repository):
    """Test that ingest returns extraction confidence."""
    with patch("kg_mcp.kg.ingest.get_llm_client", return_value=mock_llm_client):
        with patch("kg_mcp.kg.ingest.get_repository", return_value=mock_repository):
            pipeline = IngestPipeline()
            pipeline.llm = mock_llm_client
            pipeline.repo = mock_repository

            result = await pipeline.process_message(
                project_id="test-project",
                user_text="Test message",
            )

            assert "confidence" in result
            assert result["confidence"] == 0.85
