// Stalled Actions - No activity for 5+ days
// Returns neglected action items for nudge notifications

MATCH (ai:ActionItem {project_id: $project_id})
WHERE ai.status IN ['open', 'in_progress']
  AND ai.last_touched_at <= datetime() - duration('P5D')
OPTIONAL MATCH (ai)-[:ABOUT]->(t:Topic)
RETURN ai.id AS action_id,
       ai.title AS title,
       ai.last_touched_at AS last_touched,
       duration.between(ai.last_touched_at, datetime()).days AS days_stalled,
       ai.priority AS priority,
       t.name AS topic
ORDER BY ai.last_touched_at ASC
LIMIT 10
