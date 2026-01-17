"""
Prompt templates for LLM operations.
"""

from kg_mcp.llm.prompts.extractor import get_extractor_prompt
from kg_mcp.llm.prompts.linker import get_linker_prompt

__all__ = ["get_extractor_prompt", "get_linker_prompt"]
