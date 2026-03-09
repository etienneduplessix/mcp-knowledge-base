#!/usr/bin/env python3
"""
MCP Knowledge Base Server

A custom MCP server that provides tools for reading, searching, and querying
markdown and JSON files as a knowledge base for coding agents.
"""

import os
import json
import fnmatch
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional, Any
from contextlib import asynccontextmanager
from dataclasses import dataclass

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
    Resource,
    Prompt,
    PromptMessage,
    GetPromptResult,
    ServerCapabilities,
    ToolAnnotations,
)
import click


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

        If the path is absolute, use it directly.
        If the path is relative, try to resolve it against each KB base path.
        Returns the first valid resolved path.
        """
        path = Path(file_path)

        # If absolute path, use it directly
        if path.is_absolute():
            return path.resolve()

        # If relative, try to resolve against each KB base path
        for base_path in self.config.paths:
            if base_path.is_dir():
                # Try joining with this base path
                full_path = (base_path / path).resolve()
                # Check if this would be within the allowed paths
                resolved_base = base_path.resolve()
                if (
                    full_path == resolved_base
                    or resolved_base in full_path.parents
                    or full_path.parent == resolved_base
                ):
                    return full_path

        # If no match found, resolve against first KB path as fallback
        if self.config.paths:
            return (self.config.paths[0] / path).resolve()

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
    kb_paths_env = os.environ.get("KB_PATHS", "./knowledge,./docs")
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
    server = Server("knowledge-base")

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
                    title="Read Knowledge Base File",
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
                    title="Search Knowledge Base",
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
                    title="List Knowledge Base Files",
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
                    title="Get File Info",
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
                    title="Query JSON File",
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
                    title="Create Knowledge Base File",
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
                    title="Write Knowledge Base File",
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
                    title="Edit Knowledge Base File",
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
                    title="Append to Knowledge Base File",
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
                    title="Delete Knowledge Base File",
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

                result_text = f"# JSON Query Result\n\n"
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

                result_text = f"# File Created Successfully\n\n"
                result_text += f"**File:** {result['name']}\n"
                result_text += f"**Path:** {result['path']}\n"
                result_text += f"**Size:** {result['size_bytes']} bytes\n\n"
                result_text += f"✅ {result['message']}"

                return [TextContent(type="text", text=result_text)]

            elif name == "kb_write_file":
                file_path = arguments["file_path"]
                content = arguments["content"]
                result = kb.write_file(file_path, content)

                result_text = f"# File Written Successfully\n\n"
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

                result_text = f"# File Edited Successfully\n\n"
                result_text += f"**File:** {result['name']}\n"
                result_text += f"**Path:** {result['path']}\n"
                result_text += f"**Replacements:** {result['replacements']}\n\n"
                result_text += f"✅ {result['message']}"

                return [TextContent(type="text", text=result_text)]

            elif name == "kb_append_file":
                file_path = arguments["file_path"]
                content = arguments["content"]
                result = kb.append_to_file(file_path, content)

                result_text = f"# Content Appended Successfully\n\n"
                result_text += f"**File:** {result['name']}\n"
                result_text += f"**Path:** {result['path']}\n"
                result_text += f"**New Size:** {result['size_bytes']} bytes\n\n"
                result_text += f"✅ {result['message']}"

                return [TextContent(type="text", text=result_text)]

            elif name == "kb_delete_file":
                file_path = arguments["file_path"]
                result = kb.delete_file(file_path)

                result_text = f"# File Deleted Successfully\n\n"
                result_text += f"**File:** {result['name']}\n"
                result_text += f"**Path:** {result['path']}\n\n"
                result_text += f"🗑️  {result['message']}"

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


@click.command()
@click.option(
    "--path",
    "-p",
    multiple=True,
    help="Knowledge base directory or file path (can be used multiple times)",
)
@click.option(
    "--transport",
    "-t",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type (stdio or sse)",
)
@click.option("--port", default=8000, help="Port for SSE transport")
def main(path: tuple, transport: str, port: int):
    """Run the MCP Knowledge Base Server."""
    import asyncio

    # Create configuration
    if path:
        # Use command-line paths
        paths = [Path(p).resolve() for p in path]
    elif os.environ.get("KB_PATHS"):
        # Use environment variable paths (set by MCP config)
        paths = [Path(p.strip()).resolve() for p in os.environ["KB_PATHS"].split(",")]
    else:
        # Fallback to default paths
        paths = [Path("./knowledge").resolve(), Path("./docs").resolve()]

    # Ensure paths exist
    for p in paths:
        if not p.exists():
            print(f"Warning: Path does not exist: {p}")

    config = KnowledgeBaseConfig(paths=paths)

    if transport == "stdio":
        asyncio.run(serve_kb_server(config))
    else:
        print("SSE transport not yet implemented. Use stdio for now.")


if __name__ == "__main__":
    main()
