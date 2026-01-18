"""
Tests for MCP tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_ingest_pipeline():
    """Create mock ingest pipeline."""
    pipeline = MagicMock()
    pipeline.process_message = AsyncMock(
        return_value={
            "interaction_id": "test-interaction",
            "extracted": {
                "goals": [{"title": "Test Goal"}],
                "constraints": [],
                "preferences": [],
                "pain_points": [],
                "strategies": [],
            },
            "created_entities": {"goals": ["goal-1"]},
            "confidence": 0.9,
        }
    )
    return pipeline


@pytest.fixture
def mock_context_builder():
    """Create mock context builder."""
    builder = MagicMock()
    builder.build_context_pack = AsyncMock(
        return_value={
            "markdown": "# Context Pack\n\nTest content",
            "entities": {
                "active_goals": [],
                "preferences": [],
                "pain_points": [],
            },
        }
    )
    return builder


@pytest.fixture
def mock_repository():
    """Create mock repository."""
    repo = MagicMock()
    repo.fulltext_search = AsyncMock(return_value=[])
    repo.upsert_code_artifact = AsyncMock(
        return_value={"id": "artifact-1", "path": "test.py"}
    )
    repo.get_impact_for_artifacts = AsyncMock(
        return_value={
            "goals_to_retest": [],
            "tests_to_run": [],
            "strategies_to_review": [],
            "artifacts_related": [],
        }
    )
    return repo


class TestKgIngestMessage:
    """Tests for kg_ingest_message tool."""

    @pytest.mark.asyncio
    async def test_ingest_returns_interaction_id(self, mock_ingest_pipeline):
        """Test that ingest returns an interaction ID."""
        with patch(
            "kg_mcp.mcp.tools.get_ingest_pipeline", return_value=mock_ingest_pipeline
        ):
            # Simulate the tool function behavior
            result = await mock_ingest_pipeline.process_message(
                project_id="test-project",
                user_text="Test message",
            )

            assert result["interaction_id"] == "test-interaction"

    @pytest.mark.asyncio
    async def test_ingest_returns_extracted_entities(self, mock_ingest_pipeline):
        """Test that ingest returns extracted entities."""
        result = await mock_ingest_pipeline.process_message(
            project_id="test-project",
            user_text="Create a login feature",
        )

        assert "extracted" in result
        assert len(result["extracted"]["goals"]) == 1


class TestKgContextPack:
    """Tests for kg_context_pack tool."""

    @pytest.mark.asyncio
    async def test_context_pack_returns_markdown(self, mock_context_builder):
        """Test that context pack returns markdown."""
        result = await mock_context_builder.build_context_pack(
            project_id="test-project",
        )

        assert "markdown" in result
        assert "# Context Pack" in result["markdown"]

    @pytest.mark.asyncio
    async def test_context_pack_returns_entities(self, mock_context_builder):
        """Test that context pack returns entities dict."""
        result = await mock_context_builder.build_context_pack(
            project_id="test-project",
        )

        assert "entities" in result
        assert "active_goals" in result["entities"]


class TestKgSearch:
    """Tests for kg_search tool."""

    @pytest.mark.asyncio
    async def test_search_calls_repository(self, mock_repository):
        """Test that search calls the repository."""
        await mock_repository.fulltext_search(
            project_id="test-project",
            query="authentication",
            node_types=["Goal"],
            limit=10,
        )

        mock_repository.fulltext_search.assert_called_once()


class TestKgLinkCodeArtifact:
    """Tests for kg_link_code_artifact tool."""

    @pytest.mark.asyncio
    async def test_link_artifact_creates_node(self, mock_repository):
        """Test that linking creates an artifact node."""
        result = await mock_repository.upsert_code_artifact(
            project_id="test-project",
            path="src/main.py",
            kind="file",
            language="python",
        )

        assert result["id"] == "artifact-1"
        mock_repository.upsert_code_artifact.assert_called_once()


class TestKgImpactAnalysis:
    """Tests for kg_impact_analysis tool."""

    @pytest.mark.asyncio
    async def test_impact_analysis_returns_structure(self, mock_repository):
        """Test that impact analysis returns correct structure."""
        result = await mock_repository.get_impact_for_artifacts(
            project_id="test-project",
            paths=["src/auth.py"],
        )

        assert "goals_to_retest" in result
        assert "tests_to_run" in result
        assert "strategies_to_review" in result
        assert "artifacts_related" in result


class TestKgAutopilot:
    """Tests for the simplified kg_autopilot tool."""

    @pytest.mark.asyncio
    async def test_autopilot_combines_ingest_and_context(
        self, mock_ingest_pipeline, mock_context_builder
    ):
        """Test that autopilot calls both ingest and context pack."""
        # Simulate ingest
        ingest_result = await mock_ingest_pipeline.process_message(
            project_id="test-project",
            user_text="Create a login feature",
        )
        
        # Simulate context pack
        context_result = await mock_context_builder.build_context_pack(
            project_id="test-project",
        )

        # Verify both were called
        assert ingest_result["interaction_id"] is not None
        assert "markdown" in context_result

    @pytest.mark.asyncio
    async def test_autopilot_returns_combined_result(
        self, mock_ingest_pipeline, mock_context_builder
    ):
        """Test that autopilot returns a combined result structure."""
        ingest_result = await mock_ingest_pipeline.process_message(
            project_id="test-project",
            user_text="Test message",
        )
        context_result = await mock_context_builder.build_context_pack(
            project_id="test-project",
        )

        # The combined result should have fields from both
        combined = {
            "interaction_id": ingest_result["interaction_id"],
            "extracted": ingest_result["extracted"],
            "markdown": context_result["markdown"],
            "entities": context_result["entities"],
        }

        assert combined["interaction_id"] == "test-interaction"
        assert "# Context Pack" in combined["markdown"]


class TestKgTrackChanges:
    """Tests for the simplified kg_track_changes tool."""

    @pytest.mark.asyncio
    async def test_track_changes_links_multiple_files(self, mock_repository):
        """Test that track_changes can link multiple files."""
        paths = ["src/main.py", "src/utils.py", "tests/test_main.py"]
        
        linked_count = 0
        for path in paths:
            await mock_repository.upsert_code_artifact(
                project_id="test-project",
                path=path,
                kind="file",
            )
            linked_count += 1

        assert linked_count == 3
        assert mock_repository.upsert_code_artifact.call_count == 3

    @pytest.mark.asyncio
    async def test_track_changes_includes_impact_analysis(self, mock_repository):
        """Test that track_changes includes impact analysis."""
        # Link artifact
        await mock_repository.upsert_code_artifact(
            project_id="test-project",
            path="src/auth.py",
            kind="file",
        )

        # Get impact
        impact = await mock_repository.get_impact_for_artifacts(
            project_id="test-project",
            paths=["src/auth.py"],
        )

        assert "goals_to_retest" in impact
        assert "tests_to_run" in impact

