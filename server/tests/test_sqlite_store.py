"""
test_sqlite_store.py
Unit tests for Embedded SQLite Property Graph Store (zero-docker standalone mode).
"""
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from kg_mcp.kg.sqlite_store import SQLitePropertyGraphStore


def test_sqlite_store_lifecycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_memory.db"
        store = SQLitePropertyGraphStore(db_path=db_path)

        # 1. Project
        proj = store.get_or_create_project("test-proj", "Test Project")
        assert proj["id"] == "test-proj"
        assert proj["name"] == "Test Project"

        # 2. Raw Events & Screenshot deduplication
        now = datetime.now(timezone.utc)
        ev1 = store.upsert_raw_event(
            project_id="test-proj",
            event_type="screenshot",
            timestamp=now,
            data={"app": "Safari", "window": "Research"},
            text_content="User reading arxiv paper",
            screenshot_hash="dhash1234567890",
            is_duplicate=False,
        )
        assert ev1["id"] is not None

        last_shot = store.get_last_screenshot_event("test-proj")
        assert last_shot is not None
        assert last_shot["screenshot_hash"] == "dhash1234567890"

        # 3. Activity Slice
        slice_obj = store.upsert_activity_slice(
            project_id="test-proj",
            start_time=now - timedelta(minutes=30),
            end_time=now,
            summary="Coding Neural Memory standalone mode",
            event_ids=[ev1["id"]],
        )
        assert slice_obj["id"] is not None
        assert slice_obj["summary"] == "Coding Neural Memory standalone mode"

        # 4. Property Graph Nodes & Links
        store.upsert_node(
            node_id="dec_001",
            label="Decision",
            properties={"title": "Use SQLite for Standalone", "verdict": "approved"},
            project_id="test-proj",
            timestamp_iso=now.isoformat(),
        )
        store.upsert_node(
            node_id="top_001",
            label="Topic",
            properties={"name": "Storage Architecture"},
            project_id="test-proj",
            timestamp_iso=now.isoformat(),
        )
        store.upsert_link(
            source_id="dec_001",
            target_id="top_001",
            rel_type="RELATES_TO",
            properties={"weight": 1.0},
        )

        graph = store.get_graph_data(project_id="test-proj")
        assert len(graph["nodes"]) == 2
        assert len(graph["links"]) == 1
        assert graph["links"][0]["source"] == "dec_001"
        assert graph["links"][0]["target"] == "top_001"
        assert graph["links"][0]["type"] == "RELATES_TO"

        # 5. Search
        search_res = store.search("SQLite", limit=5)
        assert len(search_res) >= 1
        assert any("SQLite" in str(r) for r in search_res)

        # 6. Pruning
        pruned = store.prune_events(days=30)
        assert pruned == 0  # our event was created just now
