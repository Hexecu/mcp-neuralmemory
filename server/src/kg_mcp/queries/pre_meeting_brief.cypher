// Pre-Meeting Brief - Topic-driven context
// Returns decisions, actions, and context for meeting preparation

// Get meeting and its topics
MATCH (m:Meeting {id: $meeting_id})-[:ABOUT]->(t:Topic)

// Get recent decisions on these topics
OPTIONAL MATCH (d:Decision)-[:ABOUT]->(t)
WHERE d.decided_at >= datetime() - duration('P30D')

// Get open actions on these topics
OPTIONAL MATCH (ai:ActionItem)-[:ABOUT]->(t)
WHERE ai.status IN ['open', 'in_progress']

// Get recent insights on these topics
OPTIONAL MATCH (ins:Insight)-[:ABOUT]->(t)
WHERE ins.created_at >= datetime() - duration('P7D')

RETURN t.name AS topic,
       collect(DISTINCT {text: d.text, date: d.decided_at})[0..5] AS recent_decisions,
       collect(DISTINCT {title: ai.title, due: ai.due_at, status: ai.status})[0..10] AS open_actions,
       collect(DISTINCT {title: ins.title, summary: ins.summary})[0..3] AS recent_insights
