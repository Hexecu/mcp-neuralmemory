"""
Tests for LLM schemas validation.
"""

import pytest
from datetime import datetime

from kg_mcp.llm.schemas import (
    ExtractionResult,
    LinkingResult,
    GoalExtract,
    ConstraintExtract,
    PreferenceExtract,
    PainPointExtract,
    StrategyExtract,
    CodeReference,
    MergeSuggestion,
    RelationshipSuggestion,
    InteractionNode,
    GoalNode,
)


class TestExtractionSchemas:
    """Tests for extraction schemas."""

    def test_goal_extract_validation(self):
        """Test GoalExtract validates correctly."""
        goal = GoalExtract(
            title="Implement feature",
            description="Add new feature",
            priority=1,
            status="active",
        )

        assert goal.title == "Implement feature"
        assert goal.priority == 1
        assert goal.status == "active"

    def test_goal_extract_priority_bounds(self):
        """Test priority must be 1-5."""
        goal = GoalExtract(
            title="Test",
            priority=5,
        )
        assert goal.priority == 5

    def test_constraint_extract(self):
        """Test ConstraintExtract validation."""
        constraint = ConstraintExtract(
            type="time",
            description="Must complete by Friday",
            severity="must",
        )

        assert constraint.type == "time"
        assert constraint.severity == "must"

    def test_preference_extract(self):
        """Test PreferenceExtract validation."""
        pref = PreferenceExtract(
            category="coding_style",
            preference="Use type hints",
            strength="require",
        )

        assert pref.category == "coding_style"
        assert pref.strength == "require"

    def test_code_reference(self):
        """Test CodeReference validation."""
        ref = CodeReference(
            path="src/main.py",
            symbol="main",
            start_line=10,
            end_line=20,
            action="modify",
        )

        assert ref.path == "src/main.py"
        assert ref.action == "modify"

    def test_extraction_result_empty(self):
        """Test empty ExtractionResult."""
        result = ExtractionResult()

        assert len(result.goals) == 0
        assert len(result.constraints) == 0
        assert result.confidence == 0.8

    def test_extraction_result_with_data(self):
        """Test ExtractionResult with data."""
        result = ExtractionResult(
            goals=[GoalExtract(title="Test")],
            constraints=[ConstraintExtract(type="time", description="Test")],
            next_actions=["Action 1"],
            confidence=0.95,
        )

        assert len(result.goals) == 1
        assert len(result.constraints) == 1
        assert len(result.next_actions) == 1
        assert result.confidence == 0.95


class TestLinkingSchemas:
    """Tests for linking schemas."""

    def test_merge_suggestion(self):
        """Test MergeSuggestion validation."""
        merge = MergeSuggestion(
            new_entity_type="Goal",
            new_entity_title="New Goal",
            existing_entity_id="abc-123",
            existing_entity_title="Existing Goal",
            confidence=0.9,
            reason="Same objective",
        )

        assert merge.confidence == 0.9
        assert merge.reason == "Same objective"

    def test_relationship_suggestion(self):
        """Test RelationshipSuggestion validation."""
        rel = RelationshipSuggestion(
            source_type="Goal",
            source_title="Main Goal",
            relationship_type="DECOMPOSES_INTO",
            target_type="Goal",
            target_title="Sub Goal",
            confidence=0.85,
        )

        assert rel.relationship_type == "DECOMPOSES_INTO"

    def test_linking_result_empty(self):
        """Test empty LinkingResult."""
        result = LinkingResult()

        assert len(result.merge_suggestions) == 0
        assert len(result.relationships) == 0


class TestNodeSchemas:
    """Tests for graph node schemas."""

    def test_interaction_node(self):
        """Test InteractionNode creation."""
        node = InteractionNode(
            user_text="Test message",
            project_id="test-project",
        )

        assert node.user_text == "Test message"
        assert node.id is not None  # Auto-generated
        assert node.created_at is not None

    def test_goal_node(self):
        """Test GoalNode creation."""
        node = GoalNode(
            title="Test Goal",
            description="Description",
            project_id="test-project",
            priority=1,
        )

        assert node.title == "Test Goal"
        assert node.status == "active"  # Default
        assert node.priority == 1

    def test_node_id_uniqueness(self):
        """Test that nodes get unique IDs."""
        node1 = GoalNode(title="Goal 1", project_id="test")
        node2 = GoalNode(title="Goal 2", project_id="test")

        assert node1.id != node2.id
