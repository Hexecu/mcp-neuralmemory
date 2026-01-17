"""
Pytest configuration and shared fixtures.
"""

import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_project_id() -> str:
    """Return a sample project ID."""
    return "test-project-123"


@pytest.fixture
def sample_user_id() -> str:
    """Return a sample user ID."""
    return "test-user-456"


@pytest.fixture
def sample_goal_data() -> dict:
    """Return sample goal data."""
    return {
        "id": "goal-abc",
        "title": "Test Goal",
        "description": "A test goal for unit tests",
        "status": "active",
        "priority": 2,
        "project_id": "test-project-123",
    }


@pytest.fixture
def sample_interaction_data() -> dict:
    """Return sample interaction data."""
    return {
        "id": "interaction-xyz",
        "user_text": "Please implement feature X",
        "project_id": "test-project-123",
        "tags": ["feature", "test"],
    }


@pytest.fixture
def sample_code_artifact_data() -> dict:
    """Return sample code artifact data."""
    return {
        "id": "artifact-123",
        "path": "src/main.py",
        "kind": "file",
        "language": "python",
        "project_id": "test-project-123",
    }
