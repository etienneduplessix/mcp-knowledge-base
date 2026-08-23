#!/usr/bin/env python3
"""
MCP Knowledge Base Server

A custom MCP server that provides tools for reading, searching, and querying
markdown and JSON files as a knowledge base for coding agents.
"""

import fnmatch
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
    ToolAnnotations,
)

from code_analyzer import CodeAnalyzer, generate_sync_diff
from spec_generator import SpecContext, SpecGenerator, TechStack


@dataclass
class KnowledgeBaseConfig:
    """Configuration for the knowledge base."""

    paths: List[Path]
    file_extensions: List[str] = None
    max_file_size_mb: int = 10

    def __post_init__(self):
        if self.file_extensions is None:
            self.file_extensions = [".md", ".json"]


class KnowledgeBase:
    """Manages the knowledge base files and provides search capabilities."""

    def __init__(self, config: KnowledgeBaseConfig):
        self.config = config
        self._file_cache: Dict[Path, Dict[str, Any]] = {}

    def scan_files(self) -> List[Path]:
        """Scan all configured paths for knowledge base files."""
        files = []
        for base_path in self.config.paths:
            if not base_path.exists():
                continue

            if base_path.is_file() and self._is_valid_file(base_path):
                files.append(base_path)
            elif base_path.is_dir():
                for ext in self.config.file_extensions:
                    files.extend(base_path.rglob(f"*{ext}"))

        return sorted(set(files))

    def _is_valid_file(self, path: Path) -> bool:
        """Check if a file is a valid knowledge base file."""
        if not path.exists() or not path.is_file():
            return False

        if path.suffix not in self.config.file_extensions:
            return False

        # Check file size
        max_bytes = self.config.max_file_size_mb * 1024 * 1024
        if path.stat().st_size > max_bytes:
            return False

        return True

    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read and parse a knowledge base file."""
        path = self._resolve_kb_path(file_path)

        # Security check: ensure file is within knowledge base paths
        if not self._is_path_allowed(path):
            raise ValueError(f"Access denied: {file_path}")

        if not self._is_valid_file(path):
            raise ValueError(f"Invalid or inaccessible file: {file_path}")

        content = path.read_text(encoding="utf-8")

        result = {
            "path": str(path),
            "name": path.name,
            "extension": path.suffix,
            "size_bytes": len(content.encode("utf-8")),
            "content": content,
        }

        # Parse JSON files
        if path.suffix == ".json":
            try:
                result["parsed"] = json.loads(content)
            except json.JSONDecodeError as e:
                result["parse_error"] = str(e)

        return result

    def _is_path_allowed(self, path: Path) -> bool:
        """Check if a path is within allowed knowledge base directories."""
        try:
            resolved_path = path.resolve()
            for base_path in self.config.paths:
                resolved_base = base_path.resolve()
                if resolved_path == resolved_base or resolved_base in resolved_path.parents:
                    return True
            return False
        except (OSError, ValueError):
            return False

    def _resolve_kb_path(self, file_path: str) -> Path:
        """Resolve a file path relative to knowledge base directories.

        Resolution strategy:
        1. Absolute paths are used directly.
        2. If the first path segment matches a KB root directory name
           (e.g. "config", "knowledge"), map to that root and join the
           remainder. This avoids double-prefixing like
           "config/config/app-config.json".
        3. Otherwise try joining the relative path to each KB root,
           preferring an existing candidate.
        4. Fall back to the first KB root.
        """
        path = Path(file_path)

        # If absolute path, use it directly
        if path.is_absolute():
            return path.resolve()

        parts = list(path.parts)

        # Strategy 2: first segment names a KB root directory
        if parts:
            first = parts[0]
            for base_path in self.config.paths:
                if base_path.is_dir() and base_path.name == first:
                    candidate = (base_path / Path(*parts[1:])).resolve()
                    if parts[1:] or candidate.exists():
                        return candidate

        # Strategy 3: join relative path against each KB root
        candidates = []
        for base_path in self.config.paths:
            if base_path.is_dir():
                candidates.append((base_path / path).resolve())

        # Prefer a candidate that already exists
        for candidate in candidates:
            if candidate.exists():
                return candidate

        # Fallback: first KB root
        if candidates:
            return candidates[0]

        # Last resort: resolve against current directory
        return path.resolve()

    def search(self, query: str, file_pattern: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for text across all knowledge base files."""
        results = []
        query_lower = query.lower()

        for file_path in self.scan_files():
            # Filter by pattern if provided
            if file_pattern and not fnmatch.fnmatch(file_path.name, file_pattern):
                continue

            try:
                content = file_path.read_text(encoding="utf-8")
                if query_lower in content.lower():
                    # Find context around matches
                    lines = content.split("\n")
                    matches = []

                    for i, line in enumerate(lines):
                        if query_lower in line.lower():
                            start = max(0, i - 2)
                            end = min(len(lines), i + 3)
                            context = "\n".join(lines[start:end])
                            matches.append({"line_number": i + 1, "context": context})

                    results.append(
                        {
                            "path": str(file_path),
                            "name": file_path.name,
                            "matches_count": len(matches),
                            "matches": matches[:5],  # Limit to first 5 matches per file
                        }
                    )
            except Exception:
                continue

        return results

    def list_files(self, extension: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all available knowledge base files."""
        files = self.scan_files()

        if extension:
            files = [f for f in files if f.suffix == extension]

        return [
            {
                "path": str(f),
                "name": f.name,
                "extension": f.suffix,
                "size_bytes": f.stat().st_size,
            }
            for f in files
        ]

    def query_json(self, json_path: str, query_expression: Optional[str] = None) -> Dict[str, Any]:
        """Query JSON files using JSONPath-like expressions."""
        try:
            from jsonpath_ng import parse
            from jsonpath_ng.exceptions import JsonPathParserError
        except ImportError:
            # Fallback if jsonpath-ng is not available
            data = self.read_file(json_path)
            if "parsed" not in data:
                return {"error": "Failed to parse JSON", "data": data}

            if query_expression:
                # Simple dot notation fallback
                keys = query_expression.strip(".").split(".")
                result = data["parsed"]
                for key in keys:
                    if isinstance(result, dict) and key in result:
                        result = result[key]
                    else:
                        return {"error": f"Key not found: {key}", "data": data}
                return {"result": result, "path": json_path}

            return {"data": data["parsed"], "path": json_path}

        data = self.read_file(json_path)
        if "parsed" not in data:
            return {"error": "Failed to parse JSON", "data": data}

        if query_expression:
            try:
                jsonpath_expr = parse(query_expression)
                matches = [match.value for match in jsonpath_expr.find(data["parsed"])]
                return {
                    "matches": matches,
                    "match_count": len(matches),
                    "path": json_path,
                    "expression": query_expression,
                }
            except JsonPathParserError as e:
                return {"error": f"Invalid JSONPath expression: {e}", "path": json_path}

        return {"data": data["parsed"], "path": json_path}

    def create_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Create a new file in the knowledge base."""
        path = self._resolve_kb_path(file_path)

        # Security check: ensure file is within knowledge base paths
        if not self._is_path_allowed(path):
            raise ValueError(f"Access denied: {file_path}")

        # Check if file already exists
        if path.exists():
            raise ValueError(f"File already exists: {file_path}")

        # Check file extension
        if path.suffix not in self.config.file_extensions:
            raise ValueError(f"Invalid file extension. Allowed: {self.config.file_extensions}")

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "path": str(path),
            "name": path.name,
            "size_bytes": len(content.encode("utf-8")),
            "message": f"File created successfully: {path.name}",
        }

    def write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Write content to a file (create or overwrite)."""
        path = self._resolve_kb_path(file_path)

        # Security check
        if not self._is_path_allowed(path):
            raise ValueError(f"Access denied: {file_path}")

        # Check file extension
        if path.suffix not in self.config.file_extensions:
            raise ValueError(f"Invalid file extension. Allowed: {self.config.file_extensions}")

        # Check file size
        max_bytes = self.config.max_file_size_mb * 1024 * 1024
        if len(content.encode("utf-8")) > max_bytes:
            raise ValueError(
                f"Content exceeds maximum file size ({self.config.max_file_size_mb}MB)"
            )

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write content
        path.write_text(content, encoding="utf-8")

        return {
            "success": True,
            "path": str(path),
            "name": path.name,
            "size_bytes": len(content.encode("utf-8")),
            "message": f"File written successfully: {path.name}",
        }

    def edit_file(self, file_path: str, old_text: str, new_text: str) -> Dict[str, Any]:
        """Edit a file by replacing text."""
        path = self._resolve_kb_path(file_path)

        # Security check
        if not self._is_path_allowed(path):
            raise ValueError(f"Access denied: {file_path}")

        if not path.exists():
            raise ValueError(f"File not found: {file_path}")

        # Read current content
        content = path.read_text(encoding="utf-8")

        # Replace text
        if old_text not in content:
            raise ValueError(f"Text to replace not found in file: {old_text[:50]}...")

        new_content = content.replace(old_text, new_text, 1)

        # Write back
        path.write_text(new_content, encoding="utf-8")

        return {
            "success": True,
            "path": str(path),
            "name": path.name,
            "replacements": 1,
            "message": f"File edited successfully: {path.name}",
        }

    def append_to_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Append content to the end of a file."""
        path = self._resolve_kb_path(file_path)

        # Security check
        if not self._is_path_allowed(path):
            raise ValueError(f"Access denied: {file_path}")

        # Check file extension for new files
        if not path.exists():
            if path.suffix not in self.config.file_extensions:
                raise ValueError(f"Invalid file extension. Allowed: {self.config.file_extensions}")

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Append content
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)

        # Get new size
        new_size = path.stat().st_size

        return {
            "success": True,
            "path": str(path),
            "name": path.name,
            "size_bytes": new_size,
            "message": f"Content appended to file: {path.name}",
        }

    def delete_file(self, file_path: str) -> Dict[str, Any]:
        """Delete a file from the knowledge base."""
        path = self._resolve_kb_path(file_path)

        # Security check
        if not self._is_path_allowed(path):
            raise ValueError(f"Access denied: {file_path}")

        if not path.exists():
            raise ValueError(f"File not found: {file_path}")

        # Delete file
        path.unlink()

        return {
            "success": True,
            "path": str(path),
            "name": path.name,
            "message": f"File deleted successfully: {path.name}",
        }


def create_config_from_env() -> KnowledgeBaseConfig:
    """Create configuration from environment variables."""
    kb_paths_env = os.environ.get("KB_PATHS", "./specs,./knowledge,./docs,./config")
    paths = [Path(p.strip()).resolve() for p in kb_paths_env.split(",")]

    extensions_env = os.environ.get("KB_EXTENSIONS", ".md,.json")
    extensions = [e.strip() for e in extensions_env.split(",")]

    max_size = int(os.environ.get("KB_MAX_SIZE_MB", "10"))

    return KnowledgeBaseConfig(
        paths=paths,
        file_extensions=extensions,
        max_file_size_mb=max_size,
    )


async def serve_kb_server(config: KnowledgeBaseConfig):
    """Run the MCP knowledge base server."""
    kb = KnowledgeBase(config)
    server = Server("项目知识库")

    @server.list_resources()
    async def list_resources() -> List[Resource]:
        """List all available knowledge base files as resources."""
        resources = []
        for file_info in kb.list_files():
            mime_type = "application/json" if file_info["extension"] == ".json" else "text/markdown"
            resources.append(
                Resource(
                    uri=f"kb://{file_info['path']}",
                    name=file_info["name"],
                    mimeType=mime_type,
                    description=f"Knowledge base file: {file_info['name']}",
                )
            )
        return resources

    @server.read_resource()
    async def read_resource(uri: str) -> str:
        """Read a knowledge base file resource."""
        if not uri.startswith("kb://"):
            raise ValueError(f"Invalid resource URI: {uri}")

        file_path = uri[5:]  # Remove "kb://" prefix
        data = kb.read_file(file_path)
        return data["content"]

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available tools."""
        return [
            Tool(
                name="kb_read_file",
                description="Read the content of a specific knowledge base file (markdown or JSON). "
                "Returns the full content and parsed data for JSON files.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file to read (relative or absolute)",
                        }
                    },
                    "required": ["file_path"],
                },
                annotations=ToolAnnotations(
                    title="读取文件 / Read Knowledge Base File",
                    readOnlyHint=True,
                ),
            ),
            Tool(
                name="kb_search",
                description="Search for text across all knowledge base files. "
                "Returns files containing the query with context around matches.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Text to search for"},
                        "file_pattern": {
                            "type": "string",
                            "description": "Optional glob pattern to filter files (e.g., '*.md')",
                            "default": None,
                        },
                    },
                    "required": ["query"],
                },
                annotations=ToolAnnotations(
                    title="搜索知识库 / Search Knowledge Base",
                    readOnlyHint=True,
                ),
            ),
            Tool(
                name="kb_list_files",
                description="List all available files in the knowledge base. "
                "Optionally filter by file extension.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "extension": {
                            "type": "string",
                            "description": "Optional file extension filter (e.g., '.md', '.json')",
                            "default": None,
                        }
                    },
                },
                annotations=ToolAnnotations(
                    title="列出文件 / List Knowledge Base Files",
                    readOnlyHint=True,
                ),
            ),
            Tool(
                name="kb_get_file_info",
                description="Get metadata about a specific file in the knowledge base.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file"}
                    },
                    "required": ["file_path"],
                },
                annotations=ToolAnnotations(
                    title="文件信息 / Get File Info",
                    readOnlyHint=True,
                ),
            ),
            Tool(
                name="kb_query_json",
                description="Query JSON files using JSONPath expressions. "
                "Example expressions: '$.name', '$.items[*].title', '$..price'",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the JSON file"},
                        "expression": {
                            "type": "string",
                            "description": "JSONPath expression to query (optional - returns full JSON if not provided)",
                            "default": None,
                        },
                    },
                    "required": ["file_path"],
                },
                annotations=ToolAnnotations(
                    title="查询JSON / Query JSON File",
                    readOnlyHint=True,
                ),
            ),
            Tool(
                name="kb_create_file",
                description="Create a new file in the knowledge base. Fails if file already exists.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the new file (relative to knowledge base root)",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file",
                        },
                    },
                    "required": ["file_path", "content"],
                },
                annotations=ToolAnnotations(
                    title="创建文件 / Create Knowledge Base File",
                    readOnlyHint=False,
                ),
            ),
            Tool(
                name="kb_write_file",
                description="Write content to a file (creates or overwrites). Use with caution.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file (relative to knowledge base root)",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file",
                        },
                    },
                    "required": ["file_path", "content"],
                },
                annotations=ToolAnnotations(
                    title="写文件 / Write Knowledge Base File",
                    readOnlyHint=False,
                ),
            ),
            Tool(
                name="kb_edit_file",
                description="Edit a file by replacing specific text with new text. Only replaces first occurrence.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file to edit"},
                        "old_text": {"type": "string", "description": "Text to find and replace"},
                        "new_text": {"type": "string", "description": "Text to replace with"},
                    },
                    "required": ["file_path", "old_text", "new_text"],
                },
                annotations=ToolAnnotations(
                    title="编辑文件 / Edit Knowledge Base File",
                    readOnlyHint=False,
                ),
            ),
            Tool(
                name="kb_append_file",
                description="Append content to the end of a file. Creates file if it doesn't exist.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file"},
                        "content": {"type": "string", "description": "Content to append"},
                    },
                    "required": ["file_path", "content"],
                },
                annotations=ToolAnnotations(
                    title="追加内容 / Append to Knowledge Base File",
                    readOnlyHint=False,
                ),
            ),
            Tool(
                name="kb_delete_file",
                description="Delete a file from the knowledge base. Use with caution.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file to delete"}
                    },
                    "required": ["file_path"],
                },
                annotations=ToolAnnotations(
                    title="删除文件 / Delete Knowledge Base File",
                    readOnlyHint=False,
                ),
            ),
            Tool(
                name="kb_generate_business_spec",
                description="Generate a Business Architecture Specification / 业务架构规范. "
                "Outputs a structured markdown template covering project overview, "
                "business domain model, core processes, use cases, stakeholders, and KPIs. "
                "Optionally save to spec files in the project root for git versioning.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Name of the project"},
                        "project_description": {
                            "type": "string",
                            "description": "Brief description of the project",
                            "default": "",
                        },
                        "author": {
                            "type": "string",
                            "description": "Author name",
                            "default": "",
                        },
                        "version": {
                            "type": "string",
                            "description": "Project version",
                            "default": "1.0.0",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Optional: save spec to this file (e.g. 'specs/01-business.md')",
                            "default": "",
                        },
                    },
                    "required": ["project_name"],
                },
                annotations=ToolAnnotations(
                    title="业务架构规范 / Generate Business Architecture Spec",
                    readOnlyHint=False,
                ),
            ),
            Tool(
                name="kb_generate_tech_spec",
                description="Generate a Technical Architecture Specification / 技术架构规范. "
                "Outputs a structured markdown template covering tech stack, system "
                "architecture, data flow, API design, database design, security, and deployment.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Name of the project"},
                        "project_description": {
                            "type": "string",
                            "description": "Brief project description",
                            "default": "",
                        },
                        "author": {
                            "type": "string",
                            "description": "Author name",
                            "default": "",
                        },
                        "version": {
                            "type": "string",
                            "description": "Project version",
                            "default": "1.0.0",
                        },
                        "languages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Programming languages used",
                            "default": ["Python"],
                        },
                        "frameworks": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Frameworks and libraries",
                            "default": [],
                        },
                        "databases": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Databases used",
                            "default": [],
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Optional: save spec to this file (e.g. 'specs/02-tech.md')",
                            "default": "",
                        },
                    },
                    "required": ["project_name"],
                },
                annotations=ToolAnnotations(
                    title="技术架构规范 / Generate Technical Architecture Spec",
                    readOnlyHint=False,
                ),
            ),
            Tool(
                name="kb_generate_coding_standards_spec",
                description="Generate a Coding Standards Specification / 编码规范. "
                "Outputs a structured markdown template covering language conventions, "
                "naming, project structure, documentation, testing, and Git workflow.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Name of the project"},
                        "language": {
                            "type": "string",
                            "description": "Primary programming language",
                            "default": "Python",
                        },
                        "author": {
                            "type": "string",
                            "description": "Author name",
                            "default": "",
                        },
                        "version": {
                            "type": "string",
                            "description": "Project version",
                            "default": "1.0.0",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Optional: save spec to this file (e.g. 'specs/03-coding.md')",
                            "default": "",
                        },
                    },
                    "required": ["project_name"],
                },
                annotations=ToolAnnotations(
                    title="编码规范 / Generate Coding Standards Spec",
                    readOnlyHint=False,
                ),
            ),
            Tool(
                name="kb_generate_module_design_spec",
                description="Generate a Module Detailed Design Specification / 模块详细设计. "
                "Outputs a structured markdown template covering module overview, interfaces, "
                "data structures, core logic, dependencies, error handling, and testing strategy.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Name of the project"},
                        "module_name": {
                            "type": "string",
                            "description": "Name of the module being designed",
                        },
                        "module_description": {
                            "type": "string",
                            "description": "Description of the module's purpose",
                            "default": "",
                        },
                        "author": {
                            "type": "string",
                            "description": "Author name",
                            "default": "",
                        },
                        "version": {
                            "type": "string",
                            "description": "Project version",
                            "default": "1.0.0",
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Optional: save spec to this file (e.g. 'specs/04-module-<name>.md')",
                            "default": "",
                        },
                    },
                    "required": ["project_name", "module_name"],
                },
                annotations=ToolAnnotations(
                    title="模块详细设计 / Generate Module Design Spec",
                    readOnlyHint=False,
                ),
            ),
            Tool(
                name="kb_analyze_code",
                description="Analyze source code and extract project structure / 分析源代码. "
                "Scans Python/TypeScript/JS files, extracts classes, functions, API routes, "
                "data models, dependencies, and project config.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "source_path": {
                            "type": "string",
                            "description": "Path to the source code directory to analyze",
                        }
                    },
                    "required": ["source_path"],
                },
                annotations=ToolAnnotations(
                    title="分析代码 / Analyze Source Code",
                    readOnlyHint=True,
                ),
            ),
            Tool(
                name="kb_check_spec_drift",
                description="Compare a spec document against source code / 检查spec漂移. "
                "Detects missing/extra/changed items across classes, APIs, dependencies, "
                "languages, data models, and test coverage.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spec_path": {
                            "type": "string",
                            "description": "Path to the spec markdown file",
                        },
                        "source_path": {
                            "type": "string",
                            "description": "Path to the source code directory",
                        },
                    },
                    "required": ["spec_path", "source_path"],
                },
                annotations=ToolAnnotations(
                    title="检查漂移 / Check Spec Drift",
                    readOnlyHint=True,
                ),
            ),
            Tool(
                name="kb_sync_spec_from_code",
                description="Generate diff report to sync a spec with actual code / 同步spec到代码. "
                "Analyzes source code, compares against the spec, and produces actionable "
                "drift report showing what needs adding/removing/updating.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "spec_path": {
                            "type": "string",
                            "description": "Path to the spec markdown file to sync",
                        },
                        "source_path": {
                            "type": "string",
                            "description": "Path to the source code directory",
                        },
                    },
                    "required": ["spec_path", "source_path"],
                },
                annotations=ToolAnnotations(
                    title="同步漂移 / Sync Spec from Code",
                    readOnlyHint=False,
                ),
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[TextContent]:
        """Execute a tool."""
        try:
            if name == "kb_read_file":
                file_path = arguments["file_path"]
                data = kb.read_file(file_path)

                result = f"# File: {data['name']}\n\n"
                result += f"**Path:** {data['path']}\n"
                result += f"**Size:** {data['size_bytes']} bytes\n\n"

                if "parsed" in data:
                    result += "## Content (Parsed JSON):\n"
                    result += json.dumps(data["parsed"], indent=2)
                else:
                    result += "## Content:\n"
                    result += data["content"]

                return [TextContent(type="text", text=result)]

            elif name == "kb_search":
                query = arguments["query"]
                file_pattern = arguments.get("file_pattern")
                results = kb.search(query, file_pattern)

                if not results:
                    return [TextContent(type="text", text=f"No matches found for '{query}'.")]

                result_text = f"# Search Results for '{query}'\n\n"
                result_text += f"Found matches in {len(results)} file(s):\n\n"

                for r in results:
                    result_text += f"## {r['name']}\n"
                    result_text += f"**Path:** {r['path']}\n"
                    result_text += f"**Matches:** {r['matches_count']}\n\n"

                    for match in r["matches"]:
                        result_text += f"### Line {match['line_number']}:\n"
                        result_text += "```\n"
                        result_text += match["context"]
                        result_text += "\n```\n\n"

                return [TextContent(type="text", text=result_text)]

            elif name == "kb_list_files":
                extension = arguments.get("extension")
                files = kb.list_files(extension)

                if not files:
                    return [TextContent(type="text", text="No files found in knowledge base.")]

                result_text = "# Knowledge Base Files\n\n"
                result_text += f"Total files: {len(files)}\n\n"

                for f in files:
                    result_text += f"- **{f['name']}** ({f['extension']})\n"
                    result_text += f"  - Path: `{f['path']}`\n"
                    result_text += f"  - Size: {f['size_bytes']} bytes\n\n"

                return [TextContent(type="text", text=result_text)]

            elif name == "kb_get_file_info":
                file_path = arguments["file_path"]
                data = kb.read_file(file_path)

                result = f"# File Information: {data['name']}\n\n"
                result += f"- **Path:** {data['path']}\n"
                result += f"- **Extension:** {data['extension']}\n"
                result += f"- **Size:** {data['size_bytes']} bytes\n"

                if "parsed" in data:
                    result += "- **Type:** JSON (valid)\n"
                elif "parse_error" in data:
                    result += f"- **Type:** JSON (invalid: {data['parse_error']})\n"
                else:
                    result += "- **Type:** Text/Markdown\n"

                return [TextContent(type="text", text=result)]

            elif name == "kb_query_json":
                file_path = arguments["file_path"]
                expression = arguments.get("expression")
                result = kb.query_json(file_path, expression)

                if "error" in result:
                    return [TextContent(type="text", text=f"Error: {result['error']}")]

                result_text = "# JSON Query Result\n\n"
                result_text += f"**File:** {result['path']}\n"
                if expression:
                    result_text += f"**Expression:** `{expression}`\n"
                    result_text += f"**Matches:** {result.get('match_count', 'N/A')}\n\n"
                    result_text += "## Results:\n```json\n"
                    result_text += json.dumps(result.get("matches", result.get("result")), indent=2)
                    result_text += "\n```\n"
                else:
                    result_text += "\n## Full JSON Data:\n```json\n"
                    result_text += json.dumps(result.get("data"), indent=2)
                    result_text += "\n```\n"

                return [TextContent(type="text", text=result_text)]

            elif name == "kb_create_file":
                file_path = arguments["file_path"]
                content = arguments["content"]
                result = kb.create_file(file_path, content)

                result_text = "# File Created Successfully\n\n"
                result_text += f"**File:** {result['name']}\n"
                result_text += f"**Path:** {result['path']}\n"
                result_text += f"**Size:** {result['size_bytes']} bytes\n\n"
                result_text += f"✅ {result['message']}"

                return [TextContent(type="text", text=result_text)]

            elif name == "kb_write_file":
                file_path = arguments["file_path"]
                content = arguments["content"]
                result = kb.write_file(file_path, content)

                result_text = "# File Written Successfully\n\n"
                result_text += f"**File:** {result['name']}\n"
                result_text += f"**Path:** {result['path']}\n"
                result_text += f"**Size:** {result['size_bytes']} bytes\n\n"
                result_text += f"✅ {result['message']}"

                return [TextContent(type="text", text=result_text)]

            elif name == "kb_edit_file":
                file_path = arguments["file_path"]
                old_text = arguments["old_text"]
                new_text = arguments["new_text"]
                result = kb.edit_file(file_path, old_text, new_text)

                result_text = "# File Edited Successfully\n\n"
                result_text += f"**File:** {result['name']}\n"
                result_text += f"**Path:** {result['path']}\n"
                result_text += f"**Replacements:** {result['replacements']}\n\n"
                result_text += f"✅ {result['message']}"

                return [TextContent(type="text", text=result_text)]

            elif name == "kb_append_file":
                file_path = arguments["file_path"]
                content = arguments["content"]
                result = kb.append_to_file(file_path, content)

                result_text = "# Content Appended Successfully\n\n"
                result_text += f"**File:** {result['name']}\n"
                result_text += f"**Path:** {result['path']}\n"
                result_text += f"**New Size:** {result['size_bytes']} bytes\n\n"
                result_text += f"✅ {result['message']}"

                return [TextContent(type="text", text=result_text)]

            elif name == "kb_delete_file":
                file_path = arguments["file_path"]
                result = kb.delete_file(file_path)

                result_text = "# File Deleted Successfully\n\n"
                result_text += f"**File:** {result['name']}\n"
                result_text += f"**Path:** {result['path']}\n\n"
                result_text += f"🗑️  {result['message']}"

                return [TextContent(type="text", text=result_text)]

            elif name == "kb_generate_business_spec":
                ctx = SpecContext(
                    project_name=arguments["project_name"],
                    project_description=arguments.get("project_description", ""),
                    author=arguments.get("author", ""),
                    version=arguments.get("version", "1.0.0"),
                )
                gen = SpecGenerator(ctx)
                spec = gen.business_spec()
                file_path = arguments.get("file_path", "")
                if file_path:
                    kb.write_file(file_path, spec)
                    return [TextContent(type="text", text=f"# Business Architecture Spec Saved\n\n**File:** {file_path}\n\n{spec}")]
                return [TextContent(type="text", text=spec)]

            elif name == "kb_generate_tech_spec":
                ctx = SpecContext(
                    project_name=arguments["project_name"],
                    project_description=arguments.get("project_description", ""),
                    author=arguments.get("author", ""),
                    version=arguments.get("version", "1.0.0"),
                )
                stack = TechStack(
                    languages=arguments.get("languages", ["Python"]),
                    frameworks=arguments.get("frameworks", []),
                    databases=arguments.get("databases", []),
                )
                gen = SpecGenerator(ctx)
                spec = gen.tech_spec(stack)
                file_path = arguments.get("file_path", "")
                if file_path:
                    kb.write_file(file_path, spec)
                    return [TextContent(type="text", text=f"# Technical Architecture Spec Saved\n\n**File:** {file_path}\n\n{spec}")]
                return [TextContent(type="text", text=spec)]

            elif name == "kb_generate_coding_standards_spec":
                ctx = SpecContext(
                    project_name=arguments["project_name"],
                    language=arguments.get("language", "Python"),
                    author=arguments.get("author", ""),
                    version=arguments.get("version", "1.0.0"),
                )
                gen = SpecGenerator(ctx)
                spec = gen.coding_standards_spec()
                file_path = arguments.get("file_path", "")
                if file_path:
                    kb.write_file(file_path, spec)
                    return [TextContent(type="text", text=f"# Coding Standards Spec Saved\n\n**File:** {file_path}\n\n{spec}")]
                return [TextContent(type="text", text=spec)]

            elif name == "kb_generate_module_design_spec":
                ctx = SpecContext(
                    project_name=arguments["project_name"],
                    author=arguments.get("author", ""),
                    version=arguments.get("version", "1.0.0"),
                )
                gen = SpecGenerator(ctx)
                spec = gen.module_design_spec(
                    module_name=arguments["module_name"],
                    module_description=arguments.get("module_description", ""),
                )
                file_path = arguments.get("file_path", "")
                if file_path:
                    kb.write_file(file_path, spec)
                    return [TextContent(type="text", text=f"# Module Design Spec Saved\n\n**File:** {file_path}\n\n{spec}")]
                return [TextContent(type="text", text=spec)]

            elif name == "kb_analyze_code":
                source_path = Path(arguments["source_path"])
                if not source_path.exists():
                    return [TextContent(type="text", text=f"Error: Source path not found: {source_path}")]

                analyzer = CodeAnalyzer(source_path)
                project = analyzer.analyze()

                result_text = "# Code Analysis Report\n\n"
                result_text += f"**Source:** {project.root}\n"
                result_text += f"**Languages:** {', '.join(project.languages) or '(none detected)'}\n"
                result_text += f"**Source dirs:** {', '.join(project.source_dirs[:10])}\n"
                result_text += f"**Modules:** {len(project.modules)}\n"
                result_text += f"**Classes:** {len(project.class_names)}\n"
                result_text += f"**Functions:** {len(project.function_names)}\n"
                result_text += f"**API Routes:** {len(project.api_routes)}\n"
                result_text += f"**Data Models:** {len(project.data_models)}\n"
                result_text += f"**Dependencies:** {len(project.dependencies)}\n"
                result_text += f"**Test Files:** {len(project.test_files)}\n\n"

                if project.modules:
                    result_text += "## Modules\n\n"
                    for m in project.modules[:10]:
                        items = []
                        if m.classes:
                            items.append(f"{len(m.classes)} classes")
                        if m.functions:
                            items.append(f"{len(m.functions)} functions")
                        result_text += f"- **{m.name}.py** — {', '.join(items)}\n"
                    if len(project.modules) > 10:
                        result_text += f"- ... and {len(project.modules) - 10} more\n"
                    result_text += "\n"

                if project.api_routes:
                    result_text += "## API Routes\n\n"
                    result_text += "| Method | Path | Handler |\n"
                    result_text += "|--------|------|--------|\n"
                    for r in project.api_routes[:15]:
                        result_text += f"| {r.method} | `{r.path}` | {r.handler} |\n"
                    result_text += "\n"

                return [TextContent(type="text", text=result_text)]

            elif name == "kb_check_spec_drift":
                spec_path = Path(arguments["spec_path"])
                source_path = Path(arguments["source_path"])

                if not spec_path.exists():
                    return [TextContent(type="text", text=f"Error: Spec file not found: {spec_path}")]
                if not source_path.exists():
                    return [TextContent(type="text", text=f"Error: Source path not found: {source_path}")]

                analyzer = CodeAnalyzer(source_path)
                report = analyzer.detect_drift(spec_path)
                diff_report = generate_sync_diff(report)

                return [TextContent(type="text", text=diff_report)]

            elif name == "kb_sync_spec_from_code":
                spec_path = Path(arguments["spec_path"])
                source_path = Path(arguments["source_path"])

                if not spec_path.exists():
                    return [TextContent(type="text", text=f"Error: Spec file not found: {spec_path}")]
                if not source_path.exists():
                    return [TextContent(type="text", text=f"Error: Source path not found: {source_path}")]

                analyzer = CodeAnalyzer(source_path)
                report = analyzer.detect_drift(spec_path)

                result_text = "# Spec Sync from Code\n\n"
                result_text += f"**Spec:** {report.spec_path}\n"
                result_text += f"**Code:** {report.source_path}\n"
                result_text += f"**Drift Items:** {report.drift_count}\n\n"

                if not report.items:
                    result_text += "✅ No drift detected — spec is up to date.\n"
                    return [TextContent(type="text", text=result_text)]

                result_text += "## Drift Summary\n\n"
                result_text += "| # | Severity | Category | Item | Detail |\n"
                result_text += "|---|----------|----------|------|--------|\n"
                for i, item in enumerate(report.items, 1):
                    result_text += f"| {i} | {item.severity} | {item.category} | {item.spec_ref} | {item.detail} |\n"
                result_text += "\n"

                result_text += "## Suggested Edits\n\n"
                result_text += "Use `kb_edit_file` to apply these changes:\n\n"
                for item in report.items:
                    if item.severity == "missing":
                        result_text += f"1. **Add** `{item.spec_ref}` — {item.category} section missing\n"
                    elif item.severity == "extra":
                        result_text += f"1. **Review** `{item.spec_ref}` — no longer in code, consider removing\n"
                    elif item.severity == "changed":
                        result_text += f"1. **Update** `{item.spec_ref}` → {item.detail}\n"

                return [TextContent(type="text", text=result_text)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]

    @server.list_prompts()
    async def list_prompts() -> List[Prompt]:
        """List available prompts."""
        return [
            Prompt(
                name="kb_help",
                description="Get help with using the knowledge base tools",
                arguments=None,
            ),
            Prompt(
                name="kb_analyze_file",
                description="Analyze a knowledge base file and provide insights",
                arguments=[
                    {
                        "name": "file_path",
                        "description": "Path to the file to analyze",
                        "required": True,
                    }
                ],
            ),
        ]

    @server.get_prompt()
    async def get_prompt(name: str, arguments: dict | None = None) -> GetPromptResult:
        """Get a specific prompt."""
        if name == "kb_help":
            return GetPromptResult(
                description="Knowledge Base Help",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text="""I need help using the knowledge base MCP server. Please explain:

1. What tools are available
2. How to search for information
3. How to read files
4. How to query JSON data

Be concise and provide examples.""",
                        ),
                    )
                ],
            )

        elif name == "kb_analyze_file":
            file_path = arguments.get("file_path") if arguments else None
            return GetPromptResult(
                description="Analyze Knowledge Base File",
                messages=[
                    PromptMessage(
                        role="user",
                        content=TextContent(
                            type="text",
                            text=f"Please analyze the knowledge base file at '{file_path}'. "
                            f"Provide a summary of its contents and key information.",
                        ),
                    )
                ],
            )

        else:
            raise ValueError(f"Unknown prompt: {name}")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """项目知识库 — 知识库管理 + Spec驱动开发的MCP服务器."""
    if ctx.invoked_subcommand is None:
        # Default (no subcommand): start the MCP server
        serve_server()


@cli.command("serve")
def serve_cmd():
    """Start the MCP server."""
    serve_server()


def serve_server():
    """Start the MCP server (used by default and serve subcommand)."""
    import asyncio

    path = ()
    if os.environ.get("KB_PATHS"):
        paths = [Path(p.strip()).resolve() for p in os.environ["KB_PATHS"].split(",")]
    else:
        paths = [Path("./specs").resolve(), Path("./knowledge").resolve(), Path("./docs").resolve()]

    for p in paths:
        if not p.exists():
            print(f"Warning: Path does not exist: {p}")

    config = KnowledgeBaseConfig(paths=paths)
    asyncio.run(serve_kb_server(config))


@cli.command("init")
@click.option("--dir", "-d", "target_dir", default=".", help="Project directory to initialize")
@click.option("--name", "-n", "project_name", default="", help="Project name")
def init_cmd(target_dir: str, project_name: str):
    """Initialize specs/ and config in a project directory."""
    target = Path(target_dir).resolve()
    if not target.exists():
        click.echo(f"Error: Directory not found: {target}")
        raise SystemExit(1)

    click.echo(f"\n{'=' * 50}")
    click.echo(f"  项目知识库 — 初始化项目")
    click.echo(f"{'=' * 50}")
    click.echo(f"  目标: {target}\n")

    # Create directory structure
    dirs = ["specs", "knowledge", "docs", "config"]
    for d in dirs:
        (target / d).mkdir(parents=True, exist_ok=True)
        (target / d / ".gitkeep").touch()
        click.echo(f"  ✓ 创建 {d}/")

    # Server location
    server_path = Path(__file__).resolve()
    click.echo(f"  ✓ MCP 服务器: {server_path}")

    # Specs directory gitkeep with a note
    specs_readme = target / "specs" / "README.md"
    if not specs_readme.exists():
        specs_readme.write_text(f"""# Project Specifications

> 项目知识库 — Spec-Driven Development
> Project: {project_name or target.name}

| # | Spec | Status |
|---|------|--------|
| 1 | [业务架构规范](01-business.md) | 📝 待生成 |
| 2 | [技术架构规范](02-tech.md) | 📝 待生成 |
| 3 | [编码规范](03-coding.md) | 📝 待生成 |
| 4 | [模块详细设计](04-module-*.md) | 📝 待生成 |
""")
        click.echo(f"  ✓ 创建 specs/README.md")

    # Generate opencode.json
    opencode_config = {
        "$schema": "https://opencode.ai/config.json",
        "mcp": {
            "项目知识库": {
                "type": "local",
                "command": ["python", str(server_path)],
                "enabled": True,
                "environment": {
                    "KB_PATHS": f"{target / 'specs'},{target / 'knowledge'},{target / 'docs'},{target / 'config'}",
                    "KB_EXTENSIONS": ".md,.json",
                    "KB_MAX_SIZE_MB": "10",
                },
            }
        },
    }

    opencode_file = target / "opencode.json"
    if opencode_file.exists():
        click.echo(f"  ⚠ 已存在: opencode.json（跳过，请手动合并）")
    else:
        opencode_file.write_text(json.dumps(opencode_config, indent=2, ensure_ascii=False) + "\n")
        click.echo(f"  ✓ 创建 opencode.json")

    # .gitignore hint
    gitignore = target / ".gitignore"
    kb_entries = ["# 项目知识库", "knowledge/", "config/"]
    if gitignore.exists():
        existing = gitignore.read_text()
        new_entries = [e for e in kb_entries if e not in existing]
        if new_entries:
            with open(gitignore, "a") as f:
                f.write("\n" + "\n".join(new_entries) + "\n")
    else:
        gitignore.write_text("\n".join(kb_entries) + "\n")

    click.echo(f"  ✓ 更新 .gitignore")

    click.echo(f"\n{'=' * 50}")
    click.echo(f"  初始化完成!")
    click.echo(f"{'=' * 50}")
    click.echo(f"\n  下一步:")
    click.echo(f"  1. 生成 spec: python {server_path} gen-specs --name '{project_name or target.name}'")
    click.echo(f"  2. 启动: opencode")
    click.echo(f"  3. 使用: '用项目知识库...'")
    click.echo(f"")


@cli.command("gen-specs")
@click.option("--name", "-n", "project_name", required=True, help="Project name")
@click.option("--desc", "-d", "description", default="", help="Project description")
@click.option("--author", "-a", "author", default="", help="Author name")
@click.option("--lang", "-l", "language", default="Python", help="Primary language")
@click.option("--specs-dir", default="./specs", help="Specs output directory")
def gen_specs_cmd(project_name: str, description: str, author: str, language: str, specs_dir: str):
    """Generate initial set of spec documents."""
    from spec_generator import SpecGenerator, SpecContext, TechStack

    target = Path(specs_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)

    ctx = SpecContext(
        project_name=project_name,
        project_description=description,
        author=author,
        language=language,
    )
    gen = SpecGenerator(ctx)

    specs = [
        ("01-business.md", gen.business_spec(), "业务架构规范"),
        ("02-tech.md", gen.tech_spec(TechStack(languages=[language])), "技术架构规范"),
        ("03-coding.md", gen.coding_standards_spec(), "编码规范"),
    ]

    click.echo(f"\n  生成 specs/...")
    for filename, content, label in specs:
        path = target / filename
        path.write_text(content, encoding="utf-8")
        size = len(content.encode("utf-8"))
        click.echo(f"  ✓ {filename}  ({size} bytes) — {label}")

    click.echo(f"\n  提示: 模块详细设计请用 kb_generate_module_design_spec 按需生成")
    click.echo(f"  启动: opencode\n")


@cli.command("registry")
@click.argument("action", type=click.Choice(["list", "show", "add", "remove", "rebuild", "init", "path"]), required=False)
@click.argument("name", required=False)
def registry_cmd(action: str | None, name: str | None):
    """Manage local MCP Server registry (mcp-registry wrapper)."""
    import subprocess
    args = ["mcp-registry"]
    if action:
        args.append(action)
    if name:
        args.append(name)
    subprocess.run(args)


# ── Keep backward-compatible entry point ──

@click.command()
@click.option("--path", "-p", multiple=True, help="Knowledge base directory paths")
@click.option("--transport", "-t", type=click.Choice(["stdio", "sse"]), default="stdio")
@click.option("--port", default=8000, help="Port for SSE transport")
def main(path: tuple, transport: str, port: int):
    """[DEPRECATED] Use 'python mcp_kb_server.py serve' instead."""
    import asyncio

    if path:
        paths = [Path(p).resolve() for p in path]
    elif os.environ.get("KB_PATHS"):
        paths = [Path(p.strip()).resolve() for p in os.environ["KB_PATHS"].split(",")]
    else:
        paths = [Path("./specs").resolve(), Path("./knowledge").resolve(), Path("./docs").resolve()]

    for p in paths:
        if not p.exists():
            print(f"Warning: Path does not exist: {p}")

    config = KnowledgeBaseConfig(paths=paths)

    if transport == "stdio":
        asyncio.run(serve_kb_server(config))
    else:
        print("SSE transport not yet implemented. Use stdio for now.")


if __name__ == "__main__":
    cli()
