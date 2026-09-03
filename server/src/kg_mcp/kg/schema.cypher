// =============================================================================
// Neo4j Schema Definition for MCP-KG-Memory
// Run this script to initialize the database schema
// =============================================================================

// -----------------------------------------------------------------------------
// CONSTRAINTS (Unique keys)
// -----------------------------------------------------------------------------

// User constraints
CREATE CONSTRAINT user_id_unique IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE;

// Project constraints
CREATE CONSTRAINT project_id_unique IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

// Interaction constraints
CREATE CONSTRAINT interaction_id_unique IF NOT EXISTS
FOR (i:Interaction) REQUIRE i.id IS UNIQUE;

// Goal constraints
CREATE CONSTRAINT goal_id_unique IF NOT EXISTS
FOR (g:Goal) REQUIRE g.id IS UNIQUE;

// Constraint (node) constraints
CREATE CONSTRAINT constraint_id_unique IF NOT EXISTS
FOR (c:Constraint) REQUIRE c.id IS UNIQUE;

// Preference constraints
CREATE CONSTRAINT preference_id_unique IF NOT EXISTS
FOR (p:Preference) REQUIRE p.id IS UNIQUE;

// PainPoint constraints
CREATE CONSTRAINT painpoint_id_unique IF NOT EXISTS
FOR (pp:PainPoint) REQUIRE pp.id IS UNIQUE;

// Strategy constraints
CREATE CONSTRAINT strategy_id_unique IF NOT EXISTS
FOR (s:Strategy) REQUIRE s.id IS UNIQUE;

// Decision constraints
CREATE CONSTRAINT decision_id_unique IF NOT EXISTS
FOR (d:Decision) REQUIRE d.id IS UNIQUE;

// CodeArtifact constraints
CREATE CONSTRAINT artifact_id_unique IF NOT EXISTS
FOR (ca:CodeArtifact) REQUIRE ca.id IS UNIQUE;

// Symbol constraints (unique by FQN within project)
CREATE CONSTRAINT symbol_fqn_unique IF NOT EXISTS
FOR (s:Symbol) REQUIRE s.fqn IS UNIQUE;

// TestCase constraints
CREATE CONSTRAINT testcase_id_unique IF NOT EXISTS
FOR (tc:TestCase) REQUIRE tc.id IS UNIQUE;


// RawEvent constraints
CREATE CONSTRAINT rawevent_id_unique IF NOT EXISTS
FOR (re:RawEvent) REQUIRE re.id IS UNIQUE;

// ActivitySession constraints
CREATE CONSTRAINT activity_session_id_unique IF NOT EXISTS
FOR (s:ActivitySession) REQUIRE s.id IS UNIQUE;

// ActivitySlice constraints
CREATE CONSTRAINT activityslice_id_unique IF NOT EXISTS
FOR (as:ActivitySlice) REQUIRE as.id IS UNIQUE;

// Artifact (general) constraints
CREATE CONSTRAINT artifact_canonical_unique IF NOT EXISTS
FOR (a:Artifact) REQUIRE a.canonical_id IS UNIQUE;

// Snippet constraints
CREATE CONSTRAINT snippet_id_unique IF NOT EXISTS
FOR (s:Snippet) REQUIRE s.id IS UNIQUE;

// ============================================================================
// Semantic Entities
// ============================================================================

// Person constraints
CREATE CONSTRAINT person_name_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.name IS UNIQUE;

// Organization constraints
CREATE CONSTRAINT org_name_unique IF NOT EXISTS
FOR (o:Organization) REQUIRE o.name IS UNIQUE;

// App constraints
CREATE CONSTRAINT app_name_unique IF NOT EXISTS
FOR (a:App) REQUIRE a.name IS UNIQUE;

// Meeting constraints
CREATE CONSTRAINT meeting_id_unique IF NOT EXISTS
FOR (m:Meeting) REQUIRE m.id IS UNIQUE;

// MediaArtifact constraints (Screenshots/Audio)
CREATE CONSTRAINT mediaartifact_id_unique IF NOT EXISTS
FOR (ma:MediaArtifact) REQUIRE ma.id IS UNIQUE;

// Topic constraints
CREATE CONSTRAINT topic_name_unique IF NOT EXISTS
FOR (t:Topic) REQUIRE t.name IS UNIQUE;

// ActionItem constraints
CREATE CONSTRAINT actionitem_id_unique IF NOT EXISTS
FOR (ai:ActionItem) REQUIRE ai.id IS UNIQUE;

// Deadline constraints
CREATE CONSTRAINT deadline_id_unique IF NOT EXISTS
FOR (d:Deadline) REQUIRE d.id IS UNIQUE;

// Person constraints
CREATE CONSTRAINT person_name_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.name IS UNIQUE;

// Email constraints
CREATE CONSTRAINT person_email_unique IF NOT EXISTS
FOR (p:Person) REQUIRE p.email IS UNIQUE;

// ResearchBrief constraints
CREATE CONSTRAINT researchbrief_id_unique IF NOT EXISTS
FOR (rb:ResearchBrief) REQUIRE rb.id IS UNIQUE;

// Insight constraints (DeepSearch results)
CREATE CONSTRAINT insight_id_unique IF NOT EXISTS
FOR (ins:Insight) REQUIRE ins.id IS UNIQUE;

// NightlyReport constraints
CREATE CONSTRAINT nightlyreport_id_unique IF NOT EXISTS
FOR (nr:NightlyReport) REQUIRE nr.id IS UNIQUE;

// -----------------------------------------------------------------------------
// INDEXES (Performance)
// -----------------------------------------------------------------------------

// Project lookups
CREATE INDEX project_name_idx IF NOT EXISTS
FOR (p:Project) ON (p.name);

// Goal lookups
CREATE INDEX goal_status_idx IF NOT EXISTS
FOR (g:Goal) ON (g.status);

CREATE INDEX goal_project_idx IF NOT EXISTS
FOR (g:Goal) ON (g.project_id);

CREATE INDEX goal_priority_idx IF NOT EXISTS
FOR (g:Goal) ON (g.priority);

// Interaction lookups
CREATE INDEX interaction_project_idx IF NOT EXISTS
FOR (i:Interaction) ON (i.project_id);

CREATE INDEX interaction_timestamp_idx IF NOT EXISTS
FOR (i:Interaction) ON (i.timestamp);

// CodeArtifact lookups
CREATE INDEX artifact_path_idx IF NOT EXISTS
FOR (ca:CodeArtifact) ON (ca.path);

CREATE INDEX artifact_project_idx IF NOT EXISTS
FOR (ca:CodeArtifact) ON (ca.project_id);

// Preference lookups
CREATE INDEX preference_user_idx IF NOT EXISTS
FOR (p:Preference) ON (p.user_id);

CREATE INDEX preference_category_idx IF NOT EXISTS
FOR (p:Preference) ON (p.category);

// PainPoint lookups
CREATE INDEX painpoint_project_idx IF NOT EXISTS
FOR (pp:PainPoint) ON (pp.project_id);

CREATE INDEX painpoint_resolved_idx IF NOT EXISTS
FOR (pp:PainPoint) ON (pp.resolved);

// Symbol lookups
CREATE INDEX symbol_name_idx IF NOT EXISTS
FOR (s:Symbol) ON (s.name);

CREATE INDEX symbol_artifact_idx IF NOT EXISTS
FOR (s:Symbol) ON (s.artifact_id);

CREATE INDEX symbol_kind_idx IF NOT EXISTS
FOR (s:Symbol) ON (s.kind);

// Composite index for line range queries
CREATE INDEX symbol_lines_idx IF NOT EXISTS
FOR (s:Symbol) ON (s.line_start, s.line_end);


// RawEvent lookups
CREATE INDEX rawevent_timestamp_idx IF NOT EXISTS
FOR (re:RawEvent) ON (re.timestamp);

// ActivitySession lookups
CREATE INDEX activitysession_start_idx IF NOT EXISTS
FOR (s:ActivitySession) ON (s.start_time);

CREATE INDEX activitysession_end_idx IF NOT EXISTS
FOR (s:ActivitySession) ON (s.end_time);

// ActivitySlice lookups
CREATE INDEX activityslice_start_idx IF NOT EXISTS
FOR (as:ActivitySlice) ON (as.start_time);

CREATE INDEX activityslice_end_idx IF NOT EXISTS
FOR (as:ActivitySlice) ON (as.end_time);

// Meeting lookups
CREATE INDEX meeting_start_idx IF NOT EXISTS
FOR (m:Meeting) ON (m.start_time);

// ActionItem lookups
CREATE INDEX actionitem_status_idx IF NOT EXISTS
FOR (ai:ActionItem) ON (ai.status);

CREATE INDEX actionitem_due_idx IF NOT EXISTS
FOR (ai:ActionItem) ON (ai.due_at);

CREATE INDEX actionitem_score_idx IF NOT EXISTS
FOR (ai:ActionItem) ON (ai.score);

// Deadline lookups
CREATE INDEX deadline_due_idx IF NOT EXISTS
FOR (d:Deadline) ON (d.due_at);

// -----------------------------------------------------------------------------
// FULLTEXT INDEXES (Search)
// -----------------------------------------------------------------------------

// Fulltext search on Goal title and description
CREATE FULLTEXT INDEX goal_fulltext IF NOT EXISTS
FOR (g:Goal) ON EACH [g.title, g.description];

// Fulltext search on PainPoint
CREATE FULLTEXT INDEX painpoint_fulltext IF NOT EXISTS
FOR (pp:PainPoint) ON EACH [pp.description];

// Fulltext search on Strategy
CREATE FULLTEXT INDEX strategy_fulltext IF NOT EXISTS
FOR (s:Strategy) ON EACH [s.title, s.approach];

// Fulltext search on Decision
CREATE FULLTEXT INDEX decision_fulltext IF NOT EXISTS
FOR (d:Decision) ON EACH [d.title, d.decision, d.rationale];

// Fulltext search on CodeArtifact (path and symbol)
CREATE FULLTEXT INDEX artifact_fulltext IF NOT EXISTS
FOR (ca:CodeArtifact) ON EACH [ca.path];

// Fulltext search on Artifact (general)
CREATE FULLTEXT INDEX artifact_general_fulltext IF NOT EXISTS
FOR (a:Artifact) ON EACH [a.title, a.url_or_path, a.canonical_id];

// Fulltext search on Interaction user text
CREATE FULLTEXT INDEX interaction_fulltext IF NOT EXISTS
FOR (i:Interaction) ON EACH [i.user_text];

// Fulltext search on Symbol (name, fqn, signature)
CREATE FULLTEXT INDEX symbol_fulltext IF NOT EXISTS
FOR (s:Symbol) ON EACH [s.name, s.fqn, s.signature];


// Fulltext search on Topic
CREATE FULLTEXT INDEX topic_fulltext IF NOT EXISTS
FOR (t:Topic) ON EACH [t.name];

// Fulltext search on ActionItem
CREATE FULLTEXT INDEX actionitem_fulltext IF NOT EXISTS
FOR (ai:ActionItem) ON EACH [ai.title, ai.description];

// Fulltext search on Meeting
CREATE FULLTEXT INDEX meeting_fulltext IF NOT EXISTS
FOR (m:Meeting) ON EACH [m.title, m.summary];

// Fulltext search on RawEvent content (if indexed)
CREATE FULLTEXT INDEX rawevent_fulltext IF NOT EXISTS
FOR (re:RawEvent) ON EACH [re.text_content];

// Fulltext search on Snippet
CREATE FULLTEXT INDEX snippet_fulltext IF NOT EXISTS
FOR (s:Snippet) ON EACH [s.text];

// Fulltext search on ActivitySession (Episode)
CREATE FULLTEXT INDEX activitysession_fulltext IF NOT EXISTS
FOR (s:ActivitySession) ON EACH [s.title, s.summary, s.outcome];

// Fulltext search on Insight (DeepSearch results)
CREATE FULLTEXT INDEX insight_fulltext IF NOT EXISTS
FOR (ins:Insight) ON EACH [ins.title, ins.summary];

// -----------------------------------------------------------------------------
// VECTOR INDEXES (Semantic Search)
// -----------------------------------------------------------------------------

// Vector index on Topic embedding (for semantic similarity)
CREATE VECTOR INDEX topic_embedding_idx IF NOT EXISTS
FOR (t:Topic) ON (t.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

// Vector index on Insight embedding (for DeepSearch retrieval)
CREATE VECTOR INDEX insight_embedding_idx IF NOT EXISTS
FOR (ins:Insight) ON (ins.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

// Vector index on Snippet embedding
CREATE VECTOR INDEX snippet_embedding_idx IF NOT EXISTS
FOR (s:Snippet) ON (s.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

// Vector index on Artifact embedding
CREATE VECTOR INDEX artifact_embedding_idx IF NOT EXISTS
FOR (a:Artifact) ON (a.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};

// Vector index on ActivitySession embedding
CREATE VECTOR INDEX activitysession_embedding_idx IF NOT EXISTS
FOR (s:ActivitySession) ON (s.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}};


// -----------------------------------------------------------------------------
// SAMPLE RELATIONSHIP PATTERNS (for documentation)
// -----------------------------------------------------------------------------
// These are comments showing the expected relationship types:
//
// (User)-[:PREFERS]->(Preference)
// (User)-[:WORKS_ON]->(Project)
// (Project)-[:HAS_GOAL]->(Goal)
// (Goal)-[:DECOMPOSES_INTO]->(Goal)  -- SubGoal
// (Goal)-[:HAS_CONSTRAINT]->(Constraint)
// (Goal)-[:HAS_STRATEGY]->(Strategy)
// (Goal)-[:BLOCKED_BY]->(PainPoint)
// (Goal)-[:HAS_ACCEPTANCE_CRITERIA]->(AcceptanceCriteria)
// (PainPoint)-[:OBSERVED_IN]->(Interaction)
// (Interaction)-[:IN_PROJECT]->(Project)
// (Interaction)-[:PRODUCED]->(Goal|Strategy|Decision|PainPoint)
// (Goal)-[:IMPLEMENTED_BY]->(CodeArtifact)
// (CodeArtifact)-[:CONTAINS]->(Symbol)
// (Symbol)-[:CALLS]->(Symbol)
// (Symbol)-[:REFERENCES]->(Symbol)
// (Goal)-[:VERIFIED_BY]->(TestCase)
// (CodeArtifact)-[:COVERED_BY]->(TestCase)
// (CodeArtifact)-[:TOUCHED_IN]->(Interaction)
// (CodeArtifact)-[:CHANGED_IN]->(CodeChange)
//
// --- Mac Life Memory Relationships ---
// (ActivitySlice)-[:INCLUDES]->(RawEvent)
// (ActivitySlice)-[:HAS_ARTIFACT]->(MediaArtifact)
// (RawEvent)-[:HAS_ARTIFACT]->(MediaArtifact)
// (Meeting)-[:PARTICIPANT]->(Person)
// (ActionItem)-[:RELATED_TO]->(Topic)
// (ActionItem)-[:RELATED_TO]->(Project)
// (ActionItem)-[:ASSIGNED_TO]->(Person)
// (ActionItem)-[:DERIVED_FROM]->(ActivitySlice|Meeting)
// (Deadline)-[:DERIVED_FROM]->(ActivitySlice|Meeting)
// (Topic)-[:MENTIONED_IN]->(ActivitySlice|Meeting)
