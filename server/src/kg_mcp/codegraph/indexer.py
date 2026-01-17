"""
Code indexer for building the code graph.
V1 implementation using basic AST parsing.

For production use, consider integrating:
- Tree-sitter for multi-language parsing
- LSP integration for IDE data
- Scip/LSIF for pre-computed indices
"""

import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from kg_mcp.codegraph.model import (
    FileInfo,
    Symbol,
    SymbolKind,
    SymbolReference,
    ReferenceKind,
    SourceLocation,
    CodeGraphSnapshot,
    detect_language,
)
from kg_mcp.kg.repo import get_repository

logger = logging.getLogger(__name__)


# File patterns to ignore
IGNORE_PATTERNS = {
    "__pycache__",
    ".git",
    ".svn",
    ".hg",
    "node_modules",
    ".venv",
    "venv",
    ".env",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".coverage",
    "*.pyc",
    "*.pyo",
    "*.egg-info",
}


class CodeIndexer:
    """
    Indexes source code to build a code graph.

    This V1 implementation uses basic file parsing.
    For production, integrate tree-sitter or LSP.
    """

    def __init__(self, project_id: str, root_path: str):
        self.project_id = project_id
        self.root_path = Path(root_path).resolve()
        self.repo = get_repository()

    async def index_codebase(
        self,
        extensions: Optional[List[str]] = None,
        incremental: bool = True,
    ) -> CodeGraphSnapshot:
        """
        Index the entire codebase.

        Args:
            extensions: Optional list of file extensions to index (e.g., [".py", ".js"])
            incremental: If True, only index changed files

        Returns:
            CodeGraphSnapshot with indexed files and symbols
        """
        logger.info(f"Indexing codebase at {self.root_path}")

        # Default to common code extensions
        if extensions is None:
            extensions = [".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs"]

        files: List[FileInfo] = []
        references: List[SymbolReference] = []

        # Walk directory tree
        file_count = 0
        for root, dirs, filenames in os.walk(self.root_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self._should_ignore(d)]

            for filename in filenames:
                file_path = Path(root) / filename

                # Check extension
                if extensions and file_path.suffix.lower() not in extensions:
                    continue

                if self._should_ignore(filename):
                    continue

                try:
                    file_info = await self._index_file(file_path)
                    if file_info:
                        files.append(file_info)
                        file_count += 1

                        # Save to graph
                        await self._save_file_to_graph(file_info)
                except Exception as e:
                    logger.warning(f"Failed to index {file_path}: {e}")

        logger.info(f"Indexed {file_count} files with {sum(len(f.symbols) for f in files)} symbols")

        return CodeGraphSnapshot(
            project_id=self.project_id,
            timestamp=datetime.utcnow(),
            files=files,
            references=references,
        )

    async def _index_file(self, file_path: Path) -> Optional[FileInfo]:
        """Index a single file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            logger.debug(f"Could not read {file_path}: {e}")
            return None

        # Compute content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Get file stats
        stat = file_path.stat()
        line_count = content.count("\n") + 1

        # Detect language
        language = detect_language(str(file_path))

        # Create file info
        file_info = FileInfo(
            path=str(file_path.relative_to(self.root_path)),
            language=language,
            content_hash=content_hash,
            size_bytes=stat.st_size,
            line_count=line_count,
            last_modified=datetime.fromtimestamp(stat.st_mtime),
        )

        # Extract symbols based on language
        if language == "python":
            symbols = self._extract_python_symbols(content, file_info.path)
            for symbol in symbols:
                file_info.add_symbol(symbol)

        return file_info

    def _extract_python_symbols(self, content: str, file_path: str) -> List[Symbol]:
        """Extract symbols from Python code using AST."""
        symbols = []

        try:
            import ast

            tree = ast.parse(content)
        except SyntaxError as e:
            logger.debug(f"Syntax error in {file_path}: {e}")
            return symbols

        # Visit all nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbols.append(
                    Symbol(
                        fqn=f"{file_path}:{node.name}",
                        name=node.name,
                        kind=SymbolKind.FUNCTION,
                        location=SourceLocation(
                            file_path=file_path,
                            start_line=node.lineno,
                            end_line=node.end_lineno,
                        ),
                        signature=self._get_python_function_signature(node),
                        docstring=ast.get_docstring(node),
                    )
                )
            elif isinstance(node, ast.AsyncFunctionDef):
                symbols.append(
                    Symbol(
                        fqn=f"{file_path}:{node.name}",
                        name=node.name,
                        kind=SymbolKind.FUNCTION,
                        location=SourceLocation(
                            file_path=file_path,
                            start_line=node.lineno,
                            end_line=node.end_lineno,
                        ),
                        signature=self._get_python_function_signature(node),
                        docstring=ast.get_docstring(node),
                        modifiers=["async"],
                    )
                )
            elif isinstance(node, ast.ClassDef):
                symbols.append(
                    Symbol(
                        fqn=f"{file_path}:{node.name}",
                        name=node.name,
                        kind=SymbolKind.CLASS,
                        location=SourceLocation(
                            file_path=file_path,
                            start_line=node.lineno,
                            end_line=node.end_lineno,
                        ),
                        docstring=ast.get_docstring(node),
                    )
                )

        return symbols

    def _get_python_function_signature(self, node) -> str:
        """Extract function signature from AST node."""
        import ast

        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except:
                    pass
            args.append(arg_str)

        returns = ""
        if node.returns:
            try:
                returns = f" -> {ast.unparse(node.returns)}"
            except:
                pass

        return f"def {node.name}({', '.join(args)}){returns}"

    async def _save_file_to_graph(self, file_info: FileInfo) -> None:
        """Save file and its symbols to Neo4j."""
        # Save file as CodeArtifact
        artifact = await self.repo.upsert_code_artifact(
            project_id=self.project_id,
            path=file_info.path,
            kind="file",
            language=file_info.language,
            content_hash=file_info.content_hash,
        )

        # Save symbols
        for symbol in file_info.symbols:
            await self.repo.upsert_symbol(
                artifact_id=artifact["id"],
                fqn=symbol.fqn,
                kind=symbol.kind.value,
            )

    def _should_ignore(self, name: str) -> bool:
        """Check if a file/directory should be ignored."""
        for pattern in IGNORE_PATTERNS:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        return False


async def index_project(
    project_id: str,
    root_path: str,
    extensions: Optional[List[str]] = None,
) -> CodeGraphSnapshot:
    """
    Convenience function to index a project.

    Args:
        project_id: Project ID in the knowledge graph
        root_path: Root path of the codebase
        extensions: Optional list of extensions to index

    Returns:
        CodeGraphSnapshot with indexed content
    """
    indexer = CodeIndexer(project_id, root_path)
    return await indexer.index_codebase(extensions=extensions)
