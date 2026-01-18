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
        It guides the agent through the simplified 2-tool workflow.
        """
        return f"""# Knowledge Graph-Powered Coding Assistant

You are a coding assistant enhanced with a persistent Knowledge Graph memory.
**Project ID:** `{project_id}`

## Your Workflow (Simplified)

### 🚀 Step 1: Start Every Task with kg_autopilot

**ALWAYS** call this at the START of every task:

```
kg_autopilot(
    project_id="{project_id}",
    user_text="<paste the user's request here>",
    files=["<relevant", "files>"],
    search_query="<optional: keywords to search>"
)
```

This single call:
- ✅ Ingests and analyzes the request
- ✅ Extracts goals, constraints, preferences
- ✅ Returns the full context pack
- ✅ Optionally searches existing knowledge

**Read the returned markdown context carefully!**

### 🔗 Step 2: Track Changes with kg_track_changes

**ALWAYS** call this AFTER modifying files:

```
kg_track_changes(
    project_id="{project_id}",
    changed_paths=["path/to/modified/file.py"],
    related_goal_ids=["<goal_id from context>"]
)
```

This tracks your changes and returns impact analysis.

## Quick Reference

| When | Tool |
|------|------|
| START of every task | `kg_autopilot` |
| AFTER file changes | `kg_track_changes` |

## Important Rules

1. **Never skip kg_autopilot** at task start - it's your persistent memory
2. **Never skip kg_track_changes** after modifying code - it maintains traceability
3. **Read the context pack** - it contains goals, preferences, and pain points to avoid

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
