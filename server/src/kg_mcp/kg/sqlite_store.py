"""
sqlite_store.py
Embedded SQLite Property Graph Store for standalone, zero-docker Neural Memory distribution.
Stores nodes, links, raw events, and activity slices locally without external servers.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

DEFAULT_DB_DIR = Path.home() / "Library" / "Application Support" / "NeuralMemory"


class SQLitePropertyGraphStore:
    """Zero-configuration local embedded property graph store using SQLite."""

    def __init__(self, db_path: Optional[Path | str] = None):
        if db_path is None:
            DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)
            self.db_path = DEFAULT_DB_DIR / "memory.db"
        else:
            self.db_path = Path(db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for high concurrency
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT,
                created_at TEXT,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS raw_events (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                event_type TEXT,
                timestamp TEXT,
                data TEXT,
                text_content TEXT,
                screenshot_hash TEXT,
                is_duplicate INTEGER DEFAULT 0,
                duplicate_of TEXT,
                created_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_proj_ts ON raw_events(project_id, timestamp);
            CREATE INDEX IF NOT EXISTS idx_events_shot_hash ON raw_events(screenshot_hash);

            CREATE TABLE IF NOT EXISTS activity_slices (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                start_time TEXT,
                end_time TEXT,
                summary TEXT,
                event_ids TEXT,
                created_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_slices_proj ON activity_slices(project_id);

            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                label TEXT,
                project_id TEXT,
                properties TEXT,
                timestamp_iso TEXT,
                created_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_proj_label ON nodes(project_id, label);
            CREATE INDEX IF NOT EXISTS idx_nodes_ts ON nodes(timestamp_iso);

            CREATE TABLE IF NOT EXISTS links (
                id TEXT PRIMARY KEY,
                source_id TEXT,
                target_id TEXT,
                rel_type TEXT,
                properties TEXT,
                created_at TEXT,
                FOREIGN KEY(source_id) REFERENCES nodes(id) ON DELETE CASCADE,
                FOREIGN KEY(target_id) REFERENCES nodes(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_links_src_tgt ON links(source_id, target_id);
            """)

    # =========================================================================
    # Project Operations
    # =========================================================================

    def get_or_create_project(self, project_id: str, name: Optional[str] = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if row:
                conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, project_id))
                return dict(row)
            p_name = name or project_id
            conn.execute(
                "INSERT INTO projects (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (project_id, p_name, now, now),
            )
            return {"id": project_id, "name": p_name, "created_at": now, "updated_at": now}

    # =========================================================================
    # Raw Event Operations
    # =========================================================================

    def upsert_raw_event(
        self,
        project_id: str,
        event_type: str,
        timestamp: datetime,
        data: Dict[str, Any],
        text_content: Optional[str] = None,
        screenshot_hash: Optional[str] = None,
        is_duplicate: Optional[bool] = None,
        duplicate_of: Optional[str] = None,
    ) -> Dict[str, Any]:
        event_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        ts_str = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)

        self.get_or_create_project(project_id)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO raw_events (
                    id, project_id, event_type, timestamp, data, text_content,
                    screenshot_hash, is_duplicate, duplicate_of, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    project_id,
                    event_type,
                    ts_str,
                    json.dumps(data),
                    text_content,
                    screenshot_hash,
                    1 if is_duplicate else 0,
                    duplicate_of,
                    now,
                ),
            )
        return {
            "id": event_id,
            "project_id": project_id,
            "event_type": event_type,
            "timestamp": ts_str,
            "data": data,
            "text_content": text_content,
            "screenshot_hash": screenshot_hash,
            "is_duplicate": bool(is_duplicate),
            "duplicate_of": duplicate_of,
        }

    def get_last_screenshot_event(self, project_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM raw_events
                WHERE project_id = ? AND screenshot_hash IS NOT NULL
                ORDER BY timestamp DESC LIMIT 1
                """,
                (project_id,),
            ).fetchone()
            if not row:
                return None
            res = dict(row)
            res["data"] = json.loads(res["data"]) if res.get("data") else {}
            res["is_duplicate"] = bool(res.get("is_duplicate", 0))
            return res

    # =========================================================================
    # Activity Slice Operations
    # =========================================================================

    def upsert_activity_slice(
        self,
        project_id: str,
        start_time: datetime,
        end_time: datetime,
        summary: Optional[str] = None,
        event_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        slice_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        start_str = start_time.isoformat() if hasattr(start_time, "isoformat") else str(start_time)
        end_str = end_time.isoformat() if hasattr(end_time, "isoformat") else str(end_time)

        self.get_or_create_project(project_id)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO activity_slices (
                    id, project_id, start_time, end_time, summary, event_ids, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    slice_id,
                    project_id,
                    start_str,
                    end_str,
                    summary,
                    json.dumps(event_ids or []),
                    now,
                ),
            )
        return {
            "id": slice_id,
            "project_id": project_id,
            "start_time": start_str,
            "end_time": end_str,
            "summary": summary,
            "event_ids": event_ids or [],
        }

    # =========================================================================
    # Graph Node and Link Operations
    # =========================================================================

    def upsert_node(
        self,
        node_id: str,
        label: str,
        properties: Dict[str, Any],
        project_id: str = "default",
        timestamp_iso: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        ts = timestamp_iso or properties.get("timestamp") or properties.get("created_at") or now

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO nodes (id, label, project_id, properties, timestamp_iso, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    label = excluded.label,
                    properties = excluded.properties,
                    timestamp_iso = COALESCE(excluded.timestamp_iso, nodes.timestamp_iso)
                """,
                (node_id, label, project_id, json.dumps(properties), ts, now),
            )
        return {"id": node_id, "label": label, "properties": properties, "timestamp_iso": ts}

    def upsert_link(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        link_id = f"{source_id}_{rel_type}_{target_id}"
        now = datetime.now(timezone.utc).isoformat()
        props_str = json.dumps(properties or {})

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO links (id, source_id, target_id, rel_type, properties, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    properties = excluded.properties
                """,
                (link_id, source_id, target_id, rel_type, props_str, now),
            )
        return {
            "id": link_id,
            "source": source_id,
            "target": target_id,
            "type": rel_type,
            **(properties or {}),
        }

    def get_graph_data(
        self,
        project_id: str = "default",
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 250,
    ) -> Dict[str, Any]:
        with self._get_connection() as conn:
            query = "SELECT * FROM nodes WHERE 1=1"
            params: list[Any] = []
            if project_id and project_id != "default":
                query += " AND (project_id = ? OR project_id = 'default')"
                params.append(project_id)

            if since is not None:
                query += " AND timestamp_iso >= ?"
                params.append(since.isoformat())
            if until is not None:
                query += " AND timestamp_iso <= ?"
                params.append(until.isoformat())

            query += " ORDER BY timestamp_iso DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            nodes: list[dict[str, Any]] = []
            node_ids = set()

            for r in rows:
                props = json.loads(r["properties"]) if r["properties"] else {}
                node_ids.add(r["id"])
                nodes.append({
                    "id": r["id"],
                    "labels": [r["label"]],
                    "timestamp_iso": r["timestamp_iso"],
                    **props,
                })

            links: list[dict[str, Any]] = []
            if node_ids:
                placeholders = ",".join("?" * len(node_ids))
                link_rows = conn.execute(
                    f"""
                    SELECT * FROM links
                    WHERE source_id IN ({placeholders}) AND target_id IN ({placeholders})
                    """,
                    list(node_ids) + list(node_ids),
                ).fetchall()

                for lr in link_rows:
                    l_props = json.loads(lr["properties"]) if lr["properties"] else {}
                    links.append({
                        "source": lr["source_id"],
                        "target": lr["target_id"],
                        "type": lr["rel_type"],
                        **l_props,
                    })

            return {"nodes": nodes, "links": links}

    # =========================================================================
    # Search and Pruning
    # =========================================================================

    def search(self, query: str, limit: int = 5, project_id: str = "default") -> List[Dict[str, Any]]:
        results: list[dict[str, Any]] = []
        pattern = f"%{query}%"
        with self._get_connection() as conn:
            # 1. Search in raw_events
            e_rows = conn.execute(
                """
                SELECT id, event_type, timestamp, text_content, data FROM raw_events
                WHERE (text_content LIKE ? OR data LIKE ?)
                ORDER BY timestamp DESC LIMIT ?
                """,
                (pattern, pattern, limit),
            ).fetchall()
            for r in e_rows:
                results.append({
                    "id": r["id"],
                    "score": 0.85,
                    "event_type": r["event_type"],
                    "text": r["text_content"],
                    "timestamp": r["timestamp"],
                    "match_source": "raw_event",
                })

            # 2. Search in nodes
            n_rows = conn.execute(
                """
                SELECT id, label, properties, timestamp_iso FROM nodes
                WHERE properties LIKE ?
                ORDER BY timestamp_iso DESC LIMIT ?
                """,
                (pattern, limit),
            ).fetchall()
            for nr in n_rows:
                p = json.loads(nr["properties"]) if nr["properties"] else {}
                results.append({
                    "id": nr["id"],
                    "score": 0.90,
                    "label": nr["label"],
                    "title": p.get("title") or p.get("name") or nr["id"],
                    "properties": p,
                    "timestamp": nr["timestamp_iso"],
                    "match_source": "graph_node",
                })

        return results[:limit]

    def prune_events(self, days: int = 2) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM raw_events WHERE created_at < datetime('now', ?)",
                (f"-{days} days",),
            )
            return cursor.rowcount


_sqlite_store: Optional[SQLitePropertyGraphStore] = None


def get_sqlite_store(db_path: Optional[Path | str] = None) -> SQLitePropertyGraphStore:
    global _sqlite_store
    if _sqlite_store is None or db_path is not None:
        _sqlite_store = SQLitePropertyGraphStore(db_path=db_path)
    return _sqlite_store
