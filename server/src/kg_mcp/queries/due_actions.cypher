// Due Actions - Next 48 Hours
// Returns action items due soon for morning notifications

MATCH (ai:ActionItem {project_id: $project_id})
WHERE ai.status IN ['open', 'in_progress']
  AND ai.due_at IS NOT NULL
  AND ai.due_at <= datetime() + duration('P2D')
OPTIONAL MATCH (ai)-[:ABOUT]->(t:Topic)
OPTIONAL MATCH (ai)-[:ASSIGNED_TO]->(p:Person)
RETURN ai.id AS action_id,
       ai.title AS title,
       ai.due_at AS due_at,
       ai.urgency_score AS urgency,
       ai.priority AS priority,
       t.name AS topic,
       p.name AS assigned_to
ORDER BY ai.due_at ASC, ai.urgency_score DESC
LIMIT 10
