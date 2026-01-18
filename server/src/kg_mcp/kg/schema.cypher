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

// Fulltext search on Interaction user text
CREATE FULLTEXT INDEX interaction_fulltext IF NOT EXISTS
FOR (i:Interaction) ON EACH [i.user_text];

// Fulltext search on Symbol (name, fqn, signature)
CREATE FULLTEXT INDEX symbol_fulltext IF NOT EXISTS
FOR (s:Symbol) ON EACH [s.name, s.fqn, s.signature];


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
