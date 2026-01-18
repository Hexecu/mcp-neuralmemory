"""
Pydantic schemas for structured code change tracking.

These models define the format for kg_track_changes input,
enabling detailed tracking of file and symbol modifications.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class SymbolChange(BaseModel):
    """
    A modified symbol (function, class, method, variable).
    
    This represents a single code symbol that was added, modified, or deleted
    within a file. The agent should provide this information after making
    changes to enable precise tracking in the knowledge graph.
    
    Example:
        {
            "name": "calculate_tax",
            "kind": "function",
            "line_start": 10,
            "line_end": 25,
            "signature": "def calculate_tax(income: float) -> float",
            "change_type": "modified"
        }
    """
    
    name: str = Field(
        ..., 
        description="Symbol name. For methods, use 'ClassName.method_name' format. "
                    "Examples: 'calculate_tax', 'UserService.authenticate', 'CONFIG'"
    )
    kind: Literal["function", "method", "class", "variable"] = Field(
        ...,
        description="Type of symbol: 'function' for standalone functions, "
                    "'method' for class methods, 'class' for class definitions, "
                    "'variable' for module-level constants/variables"
    )
    line_start: int = Field(
        ..., 
        ge=1,
        description="First line number of the symbol definition (1-indexed)"
    )
    line_end: int = Field(
        ..., 
        ge=1,
        description="Last line number of the symbol definition (1-indexed)"
    )
    signature: Optional[str] = Field(
        None,
        description="Full signature including parameters and return type. "
                    "Example: 'def calculate_tax(income: float, rate: float = 0.2) -> float'"
    )
    change_type: Literal["added", "modified", "deleted", "renamed"] = Field(
        ...,
        description="What happened to this symbol: 'added' for new symbols, "
                    "'modified' for changed implementations, 'deleted' for removed symbols, "
                    "'renamed' for renamed symbols (old name)"
    )


class FileChange(BaseModel):
    """
    A single file modification with its symbols.
    
    This represents a file that was created, modified, or deleted,
    along with the specific symbols that changed within it.
    
    Example:
        {
            "path": "/project/src/utils.py",
            "change_type": "modified",
            "language": "python",
            "symbols": [
                {
                    "name": "format_currency",
                    "kind": "function",
                    "line_start": 45,
                    "line_end": 52,
                    "signature": "def format_currency(amount: float) -> str",
                    "change_type": "added"
                }
            ]
        }
    """
    
    path: str = Field(
        ...,
        description="Absolute or project-relative path to the file. "
                    "Examples: '/Users/dev/project/src/auth.py', 'src/auth.py'"
    )
    change_type: Literal["created", "modified", "deleted", "renamed"] = Field(
        ...,
        description="What happened to this file: 'created' for new files, "
                    "'modified' for changed files, 'deleted' for removed files, "
                    "'renamed' for renamed files"
    )
    language: Optional[str] = Field(
        None,
        description="Programming language. Auto-detected from extension if not provided. "
                    "Examples: 'python', 'typescript', 'javascript', 'go', 'rust'"
    )
    symbols: List[SymbolChange] = Field(
        default_factory=list,
        description="List of symbols that changed in this file. "
                    "RECOMMENDED: Always provide this for better tracking. "
                    "Include ALL functions/classes/methods that were added, modified, or deleted."
    )
    content_hash: Optional[str] = Field(
        None,
        description="SHA256 hash of file content for change detection. "
                    "Optional but useful for deduplication."
    )


class TrackChangesInput(BaseModel):
    """
    Complete input for kg_track_changes tool.
    
    This is the structured format the agent should use when calling
    kg_track_changes after making file modifications.
    """
    
    project_id: str = Field(
        ...,
        description="Project identifier. Use the workspace/repository folder name."
    )
    changes: List[FileChange] = Field(
        ...,
        min_length=1,
        description="List of file changes. Must include at least one file."
    )
    check_impact: bool = Field(
        default=True,
        description="Whether to run impact analysis to find affected goals/tests."
    )
