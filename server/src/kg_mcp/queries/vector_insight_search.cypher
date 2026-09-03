// Vector Insight Search - Semantic retrieval
// Uses vector index to find similar insights

// Note: $query_embedding must be a list of floats (1536 dimensions)
CALL db.index.vector.queryNodes('insight_embedding_idx', 8, $query_embedding)
YIELD node AS ins, score
RETURN ins.id AS insight_id,
       ins.title AS title,
       ins.summary AS summary,
       ins.url AS url,
       ins.source AS source,
       ins.created_at AS created_at,
       score
ORDER BY score DESC
