"""
Data models for code graph entities.
Represents files, symbols, and their relationships.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class SymbolKind(str, Enum):
    """Types of code symbols."""

    FILE = "file"
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    PROPERTY = "property"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    ENUM = "enum"
    TYPE_ALIAS = "type_alias"


class ReferenceKind(str, Enum):
    """Types of symbol references."""

    CALL = "call"
    IMPORT = "import"
    INHERIT = "inherit"
    IMPLEMENT = "implement"
    USE = "use"
    OVERRIDE = "override"


@dataclass
class SourceLocation:
    """Location in source code."""

    file_path: str
    start_line: int
    start_column: int = 0
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    def __post_init__(self):
        if self.end_line is None:
            self.end_line = self.start_line


@dataclass
class Symbol:
    """Represents a code symbol (function, class, variable, etc.)."""

    fqn: str  # Fully qualified name
    name: str  # Short name
    kind: SymbolKind
    location: SourceLocation
    signature: Optional[str] = None
    docstring: Optional[str] = None
    parent_fqn: Optional[str] = None  # Parent symbol (e.g., class for method)
    modifiers: List[str] = field(default_factory=list)  # public, private, static, async, etc.

    @property
    def file_path(self) -> str:
        return self.location.file_path


@dataclass
class SymbolReference:
    """Represents a reference from one symbol to another."""

    source_fqn: str  # Symbol making the reference
    target_fqn: str  # Symbol being referenced
    kind: ReferenceKind
    location: SourceLocation
    context: Optional[str] = None  # Line of code with reference


@dataclass
class FileInfo:
    """Metadata about a source file."""

    path: str
    language: str
    content_hash: str
    size_bytes: int
    line_count: int
    last_modified: datetime
    git_commit: Optional[str] = None
    symbols: List[Symbol] = field(default_factory=list)

    def add_symbol(self, symbol: Symbol) -> None:
        """Add a symbol to this file."""
        self.symbols.append(symbol)


@dataclass
class CodeGraphSnapshot:
    """A snapshot of the entire code graph."""

    project_id: str
    timestamp: datetime
    files: List[FileInfo]
    references: List[SymbolReference]

    @property
    def total_symbols(self) -> int:
        return sum(len(f.symbols) for f in self.files)

    @property
    def total_files(self) -> int:
        return len(self.files)

    @property
    def total_references(self) -> int:
        return len(self.references)


# Language detection based on file extension
LANGUAGE_EXTENSIONS = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "zsh",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".md": "markdown",
    ".rst": "rst",
}


def detect_language(file_path: str) -> str:
    """Detect language from file extension."""
    from pathlib import Path

    ext = Path(file_path).suffix.lower()
    return LANGUAGE_EXTENSIONS.get(ext, "unknown")
