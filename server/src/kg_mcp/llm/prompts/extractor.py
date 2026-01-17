"""
Extractor prompt template for entity extraction from user text.
"""

from typing import List, Optional, Tuple


EXTRACTOR_SYSTEM_PROMPT = """You are an expert at analyzing developer requests and extracting structured information.
Your task is to analyze the user's message and extract:
1. GOALS: What the user wants to achieve (objectives, features, fixes)
2. CONSTRAINTS: Limitations or requirements (budget, technology stack, performance, time)
3. PREFERENCES: User's coding/architecture preferences (patterns, styles, tools)
4. PAIN_POINTS: Problems or frustrations mentioned
5. STRATEGIES: Approaches or plans mentioned for solving problems
6. ACCEPTANCE_CRITERIA: Success conditions mentioned
7. CODE_REFERENCES: Any files, functions, classes, or code snippets referenced
8. NEXT_ACTIONS: Immediate next steps implied by the request

IMPORTANT RULES:
- Only extract information that is explicitly stated or strongly implied
- Be precise and concise in descriptions
- For code_references, extract paths exactly as mentioned
- Set confidence based on how clear the extraction is (0.0 to 1.0)
- If the message is just a greeting or acknowledgment, return empty arrays

OUTPUT FORMAT (JSON):
{
  "goals": [{"title": "...", "description": "...", "priority": 1-5, "status": "active", "parent_goal_title": null}],
  "constraints": [{"type": "budget|stack|style|performance|time", "description": "...", "severity": "must|should|nice_to_have"}],
  "preferences": [{"category": "coding_style|architecture|testing|tools|output_format", "preference": "...", "strength": "prefer|avoid|require"}],
  "pain_points": [{"description": "...", "severity": "low|medium|high|critical", "related_goal": null}],
  "strategies": [{"title": "...", "approach": "...", "rationale": "...", "related_goal": null}],
  "acceptance_criteria": [{"criterion": "...", "related_goal": "...", "testable": true}],
  "code_references": [{"path": "...", "symbol": null, "start_line": null, "end_line": null, "action": "reference|create|modify|delete"}],
  "next_actions": ["action 1", "action 2"],
  "confidence": 0.85
}"""


def get_extractor_prompt(
    user_text: str,
    files: Optional[List[str]] = None,
    diff: Optional[str] = None,
    symbols: Optional[List[str]] = None,
    context: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Build the extractor prompt for entity extraction.

    Args:
        user_text: The user's message
        files: Optional list of files involved
        diff: Optional code diff
        symbols: Optional list of symbols
        context: Optional additional context

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    user_prompt_parts = [f"USER MESSAGE:\n{user_text}"]

    if files:
        files_str = "\n".join(f"- {f}" for f in files)
        user_prompt_parts.append(f"\nFILES INVOLVED:\n{files_str}")

    if diff:
        # Truncate large diffs
        truncated_diff = diff[:2000] + "..." if len(diff) > 2000 else diff
        user_prompt_parts.append(f"\nCODE DIFF:\n```\n{truncated_diff}\n```")

    if symbols:
        symbols_str = ", ".join(symbols)
        user_prompt_parts.append(f"\nSYMBOLS REFERENCED: {symbols_str}")

    if context:
        user_prompt_parts.append(f"\nADDITIONAL CONTEXT:\n{context}")

    user_prompt_parts.append(
        "\n\nAnalyze the above and extract structured information. "
        "Return a JSON object following the specified format."
    )

    return EXTRACTOR_SYSTEM_PROMPT, "\n".join(user_prompt_parts)
