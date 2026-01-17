"""
Tests for the retrieval/context builder.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from kg_mcp.kg.retrieval import ContextBuilder


@pytest.fixture
def mock_repository():
    """Create a mock repository with sample data."""
    repo = MagicMock()

    repo.get_active_goals = AsyncMock(
        return_value=[
            {
                "id": "goal-1",
                "title": "Implement authentication",
                "description": "Add user authentication to the API",
                "status": "active",
                "priority": 1,
                "acceptance_criteria": [
                    {"criterion": "Users can register with email"},
                    {"criterion": "Users can login with password"},
                ],
                "constraints": [
                    {"description": "Use OAuth2", "severity": "must"}
                ],
                "strategies": [
                    {"title": "JWT Strategy", "approach": "Use JWT for stateless auth"}
                ],
            },
            {
                "id": "goal-2",
                "title": "Add logging",
                "description": "Implement structured logging",
                "status": "active",
                "priority": 2,
                "acceptance_criteria": [],
                "constraints": [],
                "strategies": [],
            },
        ]
    )

    repo.get_preferences = AsyncMock(
        return_value=[
            {
                "id": "pref-1",
                "category": "coding_style",
                "preference": "Use type hints",
                "strength": "require",
            },
            {
                "id": "pref-2",
                "category": "architecture",
                "preference": "Follow SOLID principles",
                "strength": "prefer",
            },
        ]
    )

    repo.get_open_painpoints = AsyncMock(
        return_value=[
            {
                "id": "pp-1",
                "description": "Database connection timeouts",
                "severity": "high",
                "blocking_goals": ["Implement authentication"],
            }
        ]
    )

    repo.get_goal_subgraph = AsyncMock(
        return_value={
            "goal": {"id": "goal-1", "title": "Implement authentication"},
            "connected": [],
        }
    )

    repo.fulltext_search = AsyncMock(return_value=[])

    repo.get_artifacts_for_goal = AsyncMock(return_value=[])

    return repo


@pytest.mark.asyncio
async def test_context_pack_includes_active_goals(mock_repository):
    """Test that context pack includes active goals."""
    with patch("kg_mcp.kg.retrieval.get_repository", return_value=mock_repository):
        builder = ContextBuilder()
        builder.repo = mock_repository

        result = await builder.build_context_pack(project_id="test-project")

        assert "markdown" in result
        assert "entities" in result
        assert "Implement authentication" in result["markdown"]
        assert "Add logging" in result["markdown"]


@pytest.mark.asyncio
async def test_context_pack_includes_preferences(mock_repository):
    """Test that context pack includes user preferences."""
    with patch("kg_mcp.kg.retrieval.get_repository", return_value=mock_repository):
        builder = ContextBuilder()
        builder.repo = mock_repository

        result = await builder.build_context_pack(project_id="test-project")

        assert "Use type hints" in result["markdown"]
        assert "SOLID principles" in result["markdown"]


@pytest.mark.asyncio
async def test_context_pack_includes_pain_points(mock_repository):
    """Test that context pack includes open pain points."""
    with patch("kg_mcp.kg.retrieval.get_repository", return_value=mock_repository):
        builder = ContextBuilder()
        builder.repo = mock_repository

        result = await builder.build_context_pack(project_id="test-project")

        assert "Database connection timeouts" in result["markdown"]
        assert "Pain Points" in result["markdown"]


@pytest.mark.asyncio
async def test_context_pack_entities_structure(mock_repository):
    """Test that entities dict has correct structure."""
    with patch("kg_mcp.kg.retrieval.get_repository", return_value=mock_repository):
        builder = ContextBuilder()
        builder.repo = mock_repository

        result = await builder.build_context_pack(project_id="test-project")

        entities = result["entities"]
        assert "active_goals" in entities
        assert "preferences" in entities
        assert "pain_points" in entities
        assert len(entities["active_goals"]) == 2
        assert len(entities["preferences"]) == 2


@pytest.mark.asyncio
async def test_context_pack_goal_priority_emoji(mock_repository):
    """Test that goals show priority emoji."""
    with patch("kg_mcp.kg.retrieval.get_repository", return_value=mock_repository):
        builder = ContextBuilder()
        builder.repo = mock_repository

        result = await builder.build_context_pack(project_id="test-project")

        # Priority 1 should have red emoji
        assert "🔴" in result["markdown"]
        # Priority 2 should have orange emoji
        assert "🟠" in result["markdown"]


@pytest.mark.asyncio
async def test_context_pack_with_focus_goal(mock_repository):
    """Test context pack with focus on specific goal."""
    with patch("kg_mcp.kg.retrieval.get_repository", return_value=mock_repository):
        builder = ContextBuilder()
        builder.repo = mock_repository

        result = await builder.build_context_pack(
            project_id="test-project",
            focus_goal_id="goal-1",
        )

        # Should have called get_goal_subgraph
        mock_repository.get_goal_subgraph.assert_called_once_with("goal-1", 2)


@pytest.mark.asyncio
async def test_context_pack_with_search_query(mock_repository):
    """Test context pack with search query."""
    mock_repository.fulltext_search = AsyncMock(
        return_value=[
            {"type": "Goal", "data": {"title": "Auth Goal"}, "score": 0.95}
        ]
    )

    with patch("kg_mcp.kg.retrieval.get_repository", return_value=mock_repository):
        builder = ContextBuilder()
        builder.repo = mock_repository

        result = await builder.build_context_pack(
            project_id="test-project",
            query="authentication",
        )

        mock_repository.fulltext_search.assert_called_once()
        assert "Search Results" in result["markdown"]


@pytest.mark.asyncio
async def test_context_pack_markdown_format(mock_repository):
    """Test that markdown is properly formatted."""
    with patch("kg_mcp.kg.retrieval.get_repository", return_value=mock_repository):
        builder = ContextBuilder()
        builder.repo = mock_repository

        result = await builder.build_context_pack(project_id="test-project")

        markdown = result["markdown"]

        # Check markdown structure
        assert markdown.startswith("# 📋 Context Pack")
        assert "## 🎯 Active Goals" in markdown
        assert "## ⚙️ User Preferences" in markdown
        assert "## ⚠️ Open Pain Points" in markdown


@pytest.mark.asyncio
async def test_context_pack_acceptance_criteria(mock_repository):
    """Test that acceptance criteria are included."""
    with patch("kg_mcp.kg.retrieval.get_repository", return_value=mock_repository):
        builder = ContextBuilder()
        builder.repo = mock_repository

        result = await builder.build_context_pack(project_id="test-project")

        assert "Users can register with email" in result["markdown"]
        assert "Users can login with password" in result["markdown"]


@pytest.mark.asyncio
async def test_context_pack_constraints(mock_repository):
    """Test that constraints are included."""
    with patch("kg_mcp.kg.retrieval.get_repository", return_value=mock_repository):
        builder = ContextBuilder()
        builder.repo = mock_repository

        result = await builder.build_context_pack(project_id="test-project")

        assert "OAuth2" in result["markdown"]
