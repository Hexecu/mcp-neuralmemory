// Top Topics - Last 2 Days
// Returns frequently accessed topics for deepsearch priority

MATCH (s:ActivitySlice)-[:ABOUT]->(t:Topic)
WHERE s.start_time >= datetime() - duration('P2D')
RETURN t.name AS topic,
       t.id AS topic_id,
       count(s) AS frequency,
       max(s.end_time) AS last_seen
ORDER BY frequency DESC, last_seen DESC
LIMIT 10
