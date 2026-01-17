"""
MCP Prompt definitions for the Knowledge Graph Memory Server.
Prompts are reusable templates that instruct agents on workflows.
"""

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_prompts(mcp: FastMCP) -> None:
    """Register all MCP prompts with the server."""

    @mcp.prompt()
    def StartCodingWithKG(project_id: str) -> str:
        """
        Instructs an IDE agent to use the Knowledge Graph for context-aware coding.

        This prompt template should be invoked at the start of a coding session.
        It guides the agent through the standard workflow:
        1. Ingest the user's request
        2. Get context from the knowledge graph
        3. Track code changes in the graph
        """
        return f"""# Knowledge Graph-Powered Coding Assistant

You are a coding assistant enhanced with a persistent Knowledge Graph memory.
**Project ID:** `{project_id}`

## Your Workflow

### Step 1: Ingest Context
At the START of every task, call the `kg_ingest_message` tool:

```
kg_ingest_message(
    project_id="{project_id}",
    user_text="<paste the user's request here>",
    files=["<list", "of", "relevant", "files>"],
    tags=["<optional>", "<tags>"]
)
```

This will:
- Create an Interaction record
- Extract goals, constraints, preferences, pain points, strategies
- Link to existing knowledge in the graph
- Return an `interaction_id` for tracking

### Step 2: Get Context Pack
After ingesting, call `kg_context_pack`:

```
kg_context_pack(
    project_id="{project_id}",
    k_hops=2
)
```

This returns a Markdown document with:
- 🎯 Active goals and acceptance criteria
- ⚙️ User preferences (coding style, patterns, tools)
- ⚠️ Open pain points to avoid
- 📁 Relevant code artifacts
- 📋 Strategies and decisions

**Use this context throughout your work!**

### Step 3: Track Code Changes
When you CREATE or MODIFY files, call `kg_link_code_artifact`:

```
kg_link_code_artifact(
    project_id="{project_id}",
    path="path/to/file.py",
    kind="file",  # or "function", "class"
    language="python",
    related_goal_ids=["<goal_id from context>"]
)
```

This enables:
- Impact analysis for future changes
- Goal-to-code traceability
- Test coverage mapping

### Step 4: Before Major Changes
Before refactoring or making breaking changes, call `kg_impact_analysis`:

```
kg_impact_analysis(
    project_id="{project_id}",
    changed_paths=["path/to/changed/file.py"]
)
```

This tells you:
- Goals that might be affected
- Tests to re-run
- Strategies that may need updating

## Important Notes

1. **Always ingest first**: The graph learns from every interaction
2. **Use the context**: Don't ask the user to repeat themselves
3. **Track your changes**: Keep the code graph updated
4. **Check impact**: Before breaking changes, understand the scope

## Quick Reference

| Tool | When to Use |
|------|-------------|
| `kg_ingest_message` | Start of every task |
| `kg_context_pack` | After ingest, to get full context |
| `kg_search` | When looking for specific information |
| `kg_link_code_artifact` | After creating/modifying files |
| `kg_impact_analysis` | Before refactoring |

---

Now, let's begin! What would you like to work on?
"""

    @mcp.prompt()
    def ReviewGoals(project_id: str) -> str:
        """
        Prompt for reviewing and managing project goals.
        """
        return f"""# Goal Review Session

**Project:** `{project_id}`

Let's review the current goals for this project.

## To Get Started

1. First, let me fetch the active goals:
   ```
   Use resource: kg://projects/{project_id}/active-goals
   ```

2. Then we can:
   - Mark goals as complete
   - Reprioritize goals
   - Break down large goals into subgoals
   - Identify blockers (pain points)
   - Update strategies

## Questions to Consider

- Are all active goals still relevant?
- Are priorities correctly assigned?
- Are there any blocked goals that need attention?
- Should any goals be decomposed into smaller tasks?

Let me retrieve the current goals and we'll discuss.
"""

    @mcp.prompt()
    def DebugWithContext(project_id: str, error_message: str = "") -> str:
        """
        Prompt for debugging with knowledge graph context.
        """
        error_section = f"\n**Error:**\n```\n{error_message}\n```\n" if error_message else ""

        return f"""# Debugging Session

**Project:** `{project_id}`
{error_section}

## Debugging Workflow

1. **Ingest the error context:**
   ```
   kg_ingest_message(
       project_id="{project_id}",
       user_text="Debugging error: {error_message[:100] if error_message else 'describe the issue'}",
       tags=["debug", "error"]
   )
   ```

2. **Get relevant context:**
   ```
   kg_context_pack(
       project_id="{project_id}",
       query="error debugging"
   )
   ```

3. **Check for known pain points:**
   - The context pack will include open pain points
   - Check if this error relates to known issues

4. **Search for related code:**
   ```
   kg_search(
       project_id="{project_id}",
       query="relevant keywords from error",
       filters=["CodeArtifact"]
   )
   ```

5. **If you find the fix**, remember to:
   - Log it as a resolved pain point
   - Link the fixed code to the goal

Let's start debugging!
"""

    @mcp.prompt()
    def DocumentPreferences(project_id: str) -> str:
        """
        Prompt for documenting user preferences.
        """
        return f"""# Preference Documentation

**Project:** `{project_id}`

I'll help you document your coding preferences. These will be remembered
and applied to all future coding tasks.

## Categories to Consider

### 1. Coding Style
- Formatting preferences (tabs vs spaces, line length)
- Naming conventions (camelCase, snake_case)
- Comment style
- Import organization

### 2. Architecture
- Design patterns preferred (SOLID, DDD, etc.)
- Architectural style (monolith, microservices)
- Error handling approach
- Logging strategy

### 3. Testing
- Test framework preference
- Coverage requirements
- Test naming conventions
- Mock/stub strategy

### 4. Tools & Technologies
- Preferred libraries
- Build tools
- Linting/formatting tools
- CI/CD preferences

### 5. Output Format
- How you like explanations formatted
- Level of detail in comments
- Documentation style

## To Record a Preference

When you tell me a preference, I'll save it using `kg_ingest_message`.
For example, if you say "I prefer functional programming patterns",
I'll extract and store that preference.

What preferences would you like to document?
"""

    logger.info("MCP prompts registered successfully")
