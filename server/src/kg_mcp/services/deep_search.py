"""
DeepSearchService - Hybrid semantic + graph + temporal search.
"""
import math
from datetime import datetime
from typing import Any, Dict, List, Optional

from kg_mcp.kg.repo import get_repository
from kg_mcp.llm.client import get_llm_client


class DeepSearchService:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.repo = get_repository()
        self.llm_client = get_llm_client()

    async def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        embedding = None
        try:
            embedding = await self.llm_client.embed(query)
        except Exception:
            embedding = None

        candidates: List[Dict[str, Any]] = []
        if embedding:
            candidates += await self._vector_search("snippet_embedding_idx", "Snippet", embedding, 8)
            candidates += await self._vector_search("artifact_embedding_idx", "Artifact", embedding, 6)
            candidates += await self._vector_search("activitysession_embedding_idx", "ActivitySession", embedding, 6)

        candidates += await self._fulltext_search("snippet_fulltext", "Snippet", query, 6)
        candidates += await self._fulltext_search("artifact_general_fulltext", "Artifact", query, 5)
        candidates += await self._fulltext_search("activitysession_fulltext", "ActivitySession", query, 5)
        candidates += await self._fulltext_search("topic_fulltext", "Topic", query, 4)

        scored = self._rerank(candidates)
        top = scored[:limit]

        enriched = []
        related = {"episodes": [], "artifacts": [], "concepts": []}
        for candidate in top:
            item, ctx = await self._expand_context(candidate)
            enriched.append(item)
            related["episodes"].extend(ctx.get("episodes", []))
            related["artifacts"].extend(ctx.get("artifacts", []))
            related["concepts"].extend(ctx.get("concepts", []))

        related = {
            "episodes": self._dedupe_nodes(related["episodes"]),
            "artifacts": self._dedupe_nodes(related["artifacts"]),
            "concepts": list({c for c in related["concepts"] if c}),
        }

        open_loops = await self._get_open_loops()

        return {
            "query": query,
            "results": enriched,
            "related": related,
            "open_loops": open_loops,
        }

    async def _vector_search(self, index_name: str, label: str, embedding: List[float], k: int) -> List[Dict[str, Any]]:
        query = f"""
        CALL db.index.vector.queryNodes('{index_name}', $k, $vector)
        YIELD node, score
        RETURN node, score
        """
        try:
            records = await self.repo.client.execute_query(query, {"k": k, "vector": embedding})
        except Exception:
            return []

        results = []
        for record in records:
            node = self._node_props(record.get("node"))
            if not node:
                continue
            results.append({
                "type": label,
                "node": node,
                "score": record.get("score", 0.0),
                "source": "vector",
            })
        return results

    async def _fulltext_search(self, index_name: str, label: str, query_str: str, k: int) -> List[Dict[str, Any]]:
        query = f"""
        CALL db.index.fulltext.queryNodes('{index_name}', $query)
        YIELD node, score
        RETURN node, score
        ORDER BY score DESC
        LIMIT $k
        """
        try:
            records = await self.repo.client.execute_query(query, {"query": query_str, "k": k})
        except Exception:
            return []

        results = []
        for record in records:
            node = self._node_props(record.get("node"))
            if not node:
                continue
            results.append({
                "type": label,
                "node": node,
                "score": record.get("score", 0.0),
                "source": "fulltext",
            })
        return results

    def _rerank(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = datetime.now()
        scored = []
        for cand in candidates:
            node = cand.get("node", {})
            base = cand.get("score", 0.0)
            recency = self._recency_score(node, now)
            centrality = node.get("interest_score", 0.0) or 0.0
            final = base * 0.6 + recency * 0.3 + min(centrality, 1.0) * 0.1
            cand["final_score"] = final
            scored.append(cand)
        scored.sort(key=lambda c: c.get("final_score", 0.0), reverse=True)
        return scored

    async def _expand_context(self, candidate: Dict[str, Any]) -> (Dict[str, Any], Dict[str, Any]):
        node = candidate.get("node", {})
        node_id = node.get("id")
        node_type = candidate.get("type")

        if node_type == "Snippet":
            return await self._expand_snippet(node_id, candidate)
        if node_type == "Artifact":
            return await self._expand_artifact(node_id, candidate)
        if node_type == "ActivitySession":
            return await self._expand_session(node_id, candidate)
        if node_type == "Topic":
            return await self._expand_topic(node.get("name"), candidate)

        return candidate, {}

    async def _expand_snippet(self, snippet_id: str, candidate: Dict[str, Any]):
        query = """
        MATCH (s:Snippet {id: $snippet_id})
        OPTIONAL MATCH (s)-[:FROM_EVENT]->(re:RawEvent)
        OPTIONAL MATCH (re)-[:IN_SLICE]->(:ActivitySlice)-[:IN_SESSION]->(ep:ActivitySession)
        OPTIONAL MATCH (re)-[:ON]->(a:Artifact)
        OPTIONAL MATCH (re)-[:MENTIONED]->(t:Topic)
        RETURN s {.*} as snippet,
               re.timestamp as seen_at,
               ep {.*} as episode,
               a {.*} as artifact,
               collect(DISTINCT t.name) as concepts
        """
        records = await self.repo.client.execute_query(query, {"snippet_id": snippet_id})
        if not records:
            return candidate, {}

        record = records[0]
        item = {
            "type": "snippet",
            "text": record["snippet"].get("text"),
            "score": candidate.get("final_score"),
            "seen_at": record.get("seen_at"),
            "episode": record.get("episode"),
            "artifact": record.get("artifact"),
            "concepts": record.get("concepts", []),
        }
        ctx = {
            "episodes": [record.get("episode")] if record.get("episode") else [],
            "artifacts": [record.get("artifact")] if record.get("artifact") else [],
            "concepts": record.get("concepts", []),
        }
        return item, ctx

    async def _expand_artifact(self, artifact_id: str, candidate: Dict[str, Any]):
        query = """
        MATCH (a:Artifact {id: $artifact_id})
        OPTIONAL MATCH (a)<-[:ON]-(re:RawEvent)-[:IN_SLICE]->(:ActivitySlice)-[:IN_SESSION]->(ep:ActivitySession)
        OPTIONAL MATCH (re)-[:MENTIONED]->(t:Topic)
        RETURN a {.*} as artifact,
               collect(DISTINCT ep {.*})[0..3] as episodes,
               collect(DISTINCT t.name) as concepts
        """
        records = await self.repo.client.execute_query(query, {"artifact_id": artifact_id})
        if not records:
            return candidate, {}

        record = records[0]
        artifact = record.get("artifact") or {}
        item = {
            "type": "artifact",
            "title": artifact.get("title"),
            "score": candidate.get("final_score"),
            "artifact": artifact,
            "concepts": record.get("concepts", []),
        }
        ctx = {
            "episodes": record.get("episodes", []),
            "artifacts": [artifact] if artifact else [],
            "concepts": record.get("concepts", []),
        }
        return item, ctx

    async def _expand_session(self, session_id: str, candidate: Dict[str, Any]):
        query = """
        MATCH (ep:ActivitySession {id: $session_id})
        OPTIONAL MATCH (ep)-[:USED_ARTIFACT]->(a:Artifact)
        OPTIONAL MATCH (ep)-[:ABOUT]->(t:Topic)
        RETURN ep {.*} as episode,
               collect(DISTINCT a {.*})[0..5] as artifacts,
               collect(DISTINCT t.name) as concepts
        """
        records = await self.repo.client.execute_query(query, {"session_id": session_id})
        if not records:
            return candidate, {}

        record = records[0]
        episode = record.get("episode") or {}
        item = {
            "type": "episode",
            "title": episode.get("title"),
            "summary": episode.get("summary"),
            "score": candidate.get("final_score"),
            "episode": episode,
            "artifacts": record.get("artifacts", []),
            "concepts": record.get("concepts", []),
        }
        ctx = {
            "episodes": [episode] if episode else [],
            "artifacts": record.get("artifacts", []),
            "concepts": record.get("concepts", []),
        }
        return item, ctx

    async def _expand_topic(self, topic_name: str, candidate: Dict[str, Any]):
        query = """
        MATCH (t:Topic {name: $topic_name})
        OPTIONAL MATCH (ep:ActivitySession)-[:ABOUT]->(t)
        OPTIONAL MATCH (a:Artifact)<-[:ON]-(:RawEvent)-[:MENTIONED]->(t)
        RETURN t.name as topic,
               collect(DISTINCT ep {.*})[0..3] as episodes,
               collect(DISTINCT a {.*})[0..3] as artifacts
        """
        records = await self.repo.client.execute_query(query, {"topic_name": topic_name})
        if not records:
            return candidate, {}

        record = records[0]
        item = {
            "type": "concept",
            "topic": record.get("topic"),
            "score": candidate.get("final_score"),
            "episodes": record.get("episodes", []),
            "artifacts": record.get("artifacts", []),
        }
        ctx = {
            "episodes": record.get("episodes", []),
            "artifacts": record.get("artifacts", []),
            "concepts": [record.get("topic")],
        }
        return item, ctx

    async def _get_open_loops(self) -> List[Dict[str, Any]]:
        query = """
        MATCH (ai:ActionItem {project_id: $project_id})
        WHERE ai.status IN ['open', 'in_progress']
        RETURN ai.title as title, ai.due_at as due_at, ai.priority as priority
        ORDER BY ai.due_at ASC
        LIMIT 5
        """
        records = await self.repo.client.execute_query(query, {"project_id": self.project_id})
        return [dict(r) for r in records]

    def _node_props(self, node: Any) -> Dict[str, Any]:
        if not node:
            return {}
        if isinstance(node, dict):
            return node
        props = getattr(node, "_properties", None)
        if props is not None:
            return dict(props)
        return {}

    def _recency_score(self, node: Dict[str, Any], now: datetime) -> float:
        ts = node.get("end_time") or node.get("last_seen_at") or node.get("created_at")
        dt = self._to_datetime(ts)
        if not dt:
            return 0.0
        if now.tzinfo is not None:
            now = now.replace(tzinfo=None)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        delta_days = max((now - dt).total_seconds() / 86400.0, 0.0)
        return math.exp(-delta_days / 7.0)

    def _to_datetime(self, ts: Any) -> Optional[datetime]:
        if ts is None:
            return None
        if isinstance(ts, datetime):
            return ts
        if hasattr(ts, "isoformat"):
            try:
                return datetime.fromisoformat(ts.isoformat())
            except Exception:
                return None
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                return None
        return None

    def _dedupe_nodes(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for node in nodes:
            if not node:
                continue
            node_id = node.get("id") or node.get("title") or node.get("name")
            if node_id in seen:
                continue
            seen.add(node_id)
            unique.append(node)
        return unique
