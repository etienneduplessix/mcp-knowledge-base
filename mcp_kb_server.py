#!/usr/bin/env python3
"""
MCP Knowledge Base Server

A custom MCP server that provides tools for reading, searching, and querying
markdown and JSON files as a knowledge base for coding agents.
"""

import os
import json
import fnmatch
import functools
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from mcp.server import MCPServer
from mcp.server.mcpserver.prompts import Prompt
from mcp.types import Resource, ToolAnnotations
import click


def _safe_tool(fn):
    """Wrap a tool function so exceptions are returned as error text."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            return f"Error: {str(e)}"

    return wrapper


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
        # Content index cache: path -> {"mtime", "size", "content", "lines"}
        self._file_cache: Dict[Path, Dict[str, Any]] = {}
        self._last_backup: Optional[str] = None

    def _load_file_to_cache(self, path: Path) -> Dict[str, Any]:
        """Load a file's content into the index cache."""
        stat = path.stat()
        content = path.read_text(encoding="utf-8")
        entry = {
            "mtime": stat.st_mtime,
            "size": stat.st_size,
            "content": content,
            "lines": content.split("\n"),
        }
        self._file_cache[path] = entry
        return entry

    def _get_cached(self, path: Path) -> Dict[str, Any]:
        """Get cached file data, transparently reloading if the file changed."""
        entry = self._file_cache.get(path)
        try:
            stat = path.stat()
        except OSError:
            self._file_cache.pop(path, None)
            raise
        if entry is None or entry["mtime"] != stat.st_mtime or entry["size"] != stat.st_size:
            return self._load_file_to_cache(path)
        return entry

    def _invalidate_cache(self, path: Path) -> None:
        """Remove a file from the index cache (e.g., after deletion)."""
        self._file_cache.pop(path, None)

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

        entry = self._get_cached(path)
        content = entry["content"]

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
        If the path is relative, try (in order):
          1. Resolve against the current working directory
          2. Resolve against each KB base path

        The caller is still responsible for the path-allowance security check
        (`_is_path_allowed`), which applies regardless of resolution strategy.
        """
        path = Path(file_path)

        # If absolute path, use it directly
        if path.is_absolute():
            return path.resolve()

        # Try resolving relative to the current working directory first
        cwd_path = path.resolve()
        if cwd_path.exists():
            return cwd_path

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
        """Search for text across all knowledge base files.

        Uses the in-memory index cache: files are read once and reused across
        searches, with mtime/size checks for automatic invalidation.
        """
        results = []
        query_lower = query.lower()

        for file_path in self.scan_files():
            # Filter by pattern if provided
            if file_pattern and not fnmatch.fnmatch(file_path.name, file_pattern):
                continue

            try:
                entry = self._get_cached(file_path)
                content = entry["content"]

                # Quick skip: query not present in this file at all
                if query_lower not in content.lower():
                    continue

                # Find context around matches
                lines = entry["lines"]
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

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get metadata about a file without reading full content.

        Markdown/text files are stat-only (no content read). JSON files are
        read to validate syntax, since that requires the parsed data.
        """
        path = self._resolve_kb_path(file_path)

        # Security check: ensure file is within knowledge base paths
        if not self._is_path_allowed(path):
            raise ValueError(f"Access denied: {file_path}")

        if not self._is_valid_file(path):
            raise ValueError(f"Invalid or inaccessible file: {file_path}")

        stat = path.stat()
        result = {
            "path": str(path),
            "name": path.name,
            "extension": path.suffix,
            "size_bytes": stat.st_size,
            "modified_at": stat.st_mtime,
        }

        # Only JSON files need full read (to validate syntax)
        if path.suffix == ".json":
            entry = self._get_cached(path)
            try:
                result["parsed"] = json.loads(entry["content"])
                result["type"] = "json_valid"
            except json.JSONDecodeError as e:
                result["type"] = "json_invalid"
                result["parse_error"] = str(e)
        else:
            result["type"] = "text_markdown"

        return result

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

    def _backup_file(self, path: Path) -> Optional[Path]:
        """Create a backup of a file before modifying it.

        Returns the backup path, or None if the file doesn't exist.
        Backups live next to the source as `<name>.<ext>.bak` and are not
        picked up by scan_files (extension filter).
        """
        if not path.exists():
            return None

        backup_path = path.with_name(path.name + ".bak")
        backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        self._last_backup = str(backup_path)
        return backup_path

    def _atomic_write(self, path: Path, content: str) -> None:
        """Atomically write content via a temp file + rename (no partial writes)."""
        temp_path = path.with_name(path.name + ".tmp")
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, path)

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

        # Backup existing file before overwriting
        self._backup_file(path)

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Write content atomically
        self._atomic_write(path, content)

        # Refresh index cache
        self._load_file_to_cache(path)

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

        # Read current content (from cache)
        entry = self._get_cached(path)
        content = entry["content"]

        # Replace text
        if old_text not in content:
            raise ValueError(f"Text to replace not found in file: {old_text[:50]}...")

        new_content = content.replace(old_text, new_text, 1)

        # Backup before modifying
        self._backup_file(path)

        # Write back atomically
        self._atomic_write(path, new_content)

        # Refresh index cache
        self._load_file_to_cache(path)

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

        # Backup existing file before appending
        self._backup_file(path)

        # Create parent directories if needed
        path.parent.mkdir(parents=True, exist_ok=True)

        # Append content
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)

        # Refresh index cache
        self._load_file_to_cache(path)

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

        # Backup before deleting (recoverable delete)
        self._backup_file(path)

        # Delete file
        path.unlink()

        # Remove from cache
        self._invalidate_cache(path)

        return {
            "success": True,
            "path": str(path),
            "name": path.name,
            "message": f"File deleted successfully: {path.name}",
        }

    def restore_from_backup(self, file_path: str) -> Dict[str, Any]:
        """Restore a file from its most recent backup (`<name>.<ext>.bak`)."""
        path = self._resolve_kb_path(file_path)

        # Security check
        if not self._is_path_allowed(path):
            raise ValueError(f"Access denied: {file_path}")

        backup_path = path.with_name(path.name + ".bak")
        if not backup_path.exists():
            raise ValueError(f"No backup found for file: {file_path}")

        # Restore atomically
        self._atomic_write(path, backup_path.read_text(encoding="utf-8"))
        self._load_file_to_cache(path)

        return {
            "success": True,
            "path": str(path),
            "name": path.name,
            "message": f"File restored from backup: {path.name}",
        }

    def process_media(self, file_path: str, contact_name: Optional[str] = None) -> Dict[str, Any]:
        """Process a media file (image OCR / audio transcription).

        Media files must be located within the knowledge base paths. On
        success, a JSON metadata record is saved into the knowledge base.
        """
        path = self._resolve_kb_path(file_path)

        # Security check: ensure file is within knowledge base paths
        if not self._is_path_allowed(path):
            raise ValueError(f"Access denied: {file_path}")

        if not path.exists() or not path.is_file():
            raise ValueError(f"File not found: {file_path}")

        try:
            from media_processor import (
                create_media_record,
                get_file_info,
                process_audio,
                process_image,
                process_video,
            )
        except ImportError:
            return {"success": False, "error": "media_processor module not available"}

        file_type, ext = get_file_info(str(path))
        if file_type == "unknown":
            return {"success": False, "error": f"Unsupported media type: {ext}"}

        # Process based on type
        if file_type == "image":
            result = process_image(str(path))
        elif file_type == "audio":
            result = process_audio(str(path))
        elif file_type == "video":
            result = process_video(str(path))
        else:
            result = {"success": False, "error": f"Media type not supported: {file_type}"}

        if not result.get("success"):
            return result

        # Create a metadata record and save it into the knowledge base
        record = create_media_record(str(path), result, contact_name)
        result["record"] = record
        try:
            result["record_path"] = self._save_media_record(path, record)
            result["record_saved"] = True
        except Exception as e:
            result["record_saved"] = False
            result["record_error"] = str(e)

        return result

    def _save_media_record(self, media_path: Path, record: Dict[str, Any]) -> str:
        """Save a media processing record as JSON inside the knowledge base."""
        media_dir = media_path.parent / "media_records"
        media_dir.mkdir(parents=True, exist_ok=True)
        record_path = media_dir / f"{media_path.stem}.json"
        record_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return str(record_path)


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


def create_kb_server(config: KnowledgeBaseConfig) -> MCPServer:
    """Create and configure the MCP server (mcp 2.x high-level API).

    Tools are registered as plain functions with schemas generated from
    their signatures; resources are registered statically at startup.
    """
    kb = KnowledgeBase(config)

    server = MCPServer(
        "knowledge-base",
        title="Knowledge Base",
        description="Read, search, and query markdown/JSON files as a knowledge base.",
        version="1.0.0",
    )

    # ── Resources ──────────────────────────────────────────
    for file_info in kb.list_files():
        mime_type = (
            "application/json" if file_info["extension"] == ".json" else "text/markdown"
        )
        server.add_resource(
            Resource(
                uri=f"kb://{file_info['name']}",
                name=file_info["name"],
                mimeType=mime_type,
                description=f"Knowledge base file: {file_info['name']}",
            )
        )

    # ── Tools ──────────────────────────────────────────────

    @server.add_tool
    @_safe_tool
    def kb_read_file(file_path: str) -> str:
        """Read a knowledge base file.

        Args:
            file_path: Path to the file to read (relative or absolute).
        """
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
        return result

    @server.add_tool
    @_safe_tool
    def kb_search(query: str, file_pattern: str | None = None) -> str:
        """Search the knowledge base.

        Args:
            query: Text to search for.
            file_pattern: Optional glob pattern to filter files (e.g. '*.md').
        """
        results = kb.search(query, file_pattern)
        if not results:
            return f"No matches found for '{query}'."

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
        return result_text

    @server.add_tool
    @_safe_tool
    def kb_list_files(extension: str | None = None) -> str:
        """List knowledge base files.

        Args:
            extension: Optional file extension filter (e.g. '.md', '.json').
        """
        files = kb.list_files(extension)
        if not files:
            return "No files found in knowledge base."

        result_text = "# Knowledge Base Files\n\n"
        result_text += f"Total files: {len(files)}\n\n"
        for f in files:
            result_text += f"- **{f['name']}** ({f['extension']})\n"
            result_text += f"  - Path: `{f['path']}`\n"
            result_text += f"  - Size: {f['size_bytes']} bytes\n\n"
        return result_text

    @server.add_tool
    @_safe_tool
    def kb_get_file_info(file_path: str) -> str:
        """Get file metadata.

        Args:
            file_path: Path to the file.
        """
        data = kb.get_file_info(file_path)
        result = f"# File Information: {data['name']}\n\n"
        result += f"- **Path:** {data['path']}\n"
        result += f"- **Extension:** {data['extension']}\n"
        result += f"- **Size:** {data['size_bytes']} bytes\n"
        if data.get("type") == "json_valid":
            result += "- **Type:** JSON (valid)\n"
        elif data.get("type") == "json_invalid":
            result += f"- **Type:** JSON (invalid: {data.get('parse_error')})\n"
        else:
            result += "- **Type:** Text/Markdown\n"
        return result

    @server.add_tool
    @_safe_tool
    def kb_query_json(file_path: str, expression: str | None = None) -> str:
        """Query a JSON file.

        Args:
            file_path: Path to the JSON file.
            expression: JSONPath expression (optional - returns full JSON if not provided).
        """
        result = kb.query_json(file_path, expression)
        if "error" in result:
            return f"Error: {result['error']}"

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
        return result_text

    @server.add_tool
    @_safe_tool
    def kb_create_file(file_path: str, content: str) -> str:
        """Create a new knowledge base file.

        Args:
            file_path: Path to the new file (relative to knowledge base root).
            content: Content to write to the file.
        """
        result = kb.create_file(file_path, content)
        result_text = "# File Created Successfully\n\n"
        result_text += f"**File:** {result['name']}\n"
        result_text += f"**Path:** {result['path']}\n"
        result_text += f"**Size:** {result['size_bytes']} bytes\n\n"
        result_text += f"✅ {result['message']}"
        return result_text

    @server.add_tool
    @_safe_tool
    def kb_write_file(file_path: str, content: str) -> str:
        """Write content to a knowledge base file.

        Args:
            file_path: Path to the file (relative to knowledge base root).
            content: Content to write to the file.
        """
        result = kb.write_file(file_path, content)
        result_text = "# File Written Successfully\n\n"
        result_text += f"**File:** {result['name']}\n"
        result_text += f"**Path:** {result['path']}\n"
        result_text += f"**Size:** {result['size_bytes']} bytes\n\n"
        result_text += f"✅ {result['message']}"
        return result_text

    @server.add_tool
    @_safe_tool
    def kb_edit_file(file_path: str, old_text: str, new_text: str) -> str:
        """Edit a knowledge base file.

        Args:
            file_path: Path to the file to edit.
            old_text: Text to find and replace.
            new_text: Text to replace with.
        """
        result = kb.edit_file(file_path, old_text, new_text)
        result_text = "# File Edited Successfully\n\n"
        result_text += f"**File:** {result['name']}\n"
        result_text += f"**Path:** {result['path']}\n"
        result_text += f"**Replacements:** {result['replacements']}\n\n"
        result_text += f"✅ {result['message']}"
        return result_text

    @server.add_tool
    @_safe_tool
    def kb_append_file(file_path: str, content: str) -> str:
        """Append content to a knowledge base file.

        Args:
            file_path: Path to the file.
            content: Content to append.
        """
        result = kb.append_to_file(file_path, content)
        result_text = "# Content Appended Successfully\n\n"
        result_text += f"**File:** {result['name']}\n"
        result_text += f"**Path:** {result['path']}\n"
        result_text += f"**New Size:** {result['size_bytes']} bytes\n\n"
        result_text += f"✅ {result['message']}"
        return result_text

    @server.add_tool
    @_safe_tool
    def kb_delete_file(file_path: str) -> str:
        """Delete a knowledge base file.

        Args:
            file_path: Path to the file to delete.
        """
        result = kb.delete_file(file_path)
        result_text = "# File Deleted Successfully\n\n"
        result_text += f"**File:** {result['name']}\n"
        result_text += f"**Path:** {result['path']}\n\n"
        result_text += f"🗑️  {result['message']}"
        return result_text

    @server.add_tool
    @_safe_tool
    def kb_restore_backup(file_path: str) -> str:
        """Restore a knowledge base file from its backup.

        Args:
            file_path: Path to the file to restore.
        """
        result = kb.restore_from_backup(file_path)
        result_text = "# File Restored From Backup\n\n"
        result_text += f"**File:** {result['name']}\n"
        result_text += f"**Path:** {result['path']}\n\n"
        result_text += f"✅ {result['message']}"
        return result_text

    @server.add_tool
    @_safe_tool
    def kb_process_media(file_path: str, contact_name: str | None = None) -> str:
        """Process a media file.

        Args:
            file_path: Path to the media file.
            contact_name: Optional contact name to link the media record.
        """
        result = kb.process_media(file_path, contact_name)
        result_text = "# Media Processing Result\n\n"
        if result.get("success"):
            result_text += f"**Type:** {result.get('type')}\n"
            if result.get("extracted_text"):
                result_text += f"\n## Extracted Text:\n{result['extracted_text']}\n"
            if result.get("transcript"):
                result_text += (
                    f"\n## Transcript ({result.get('language', 'unknown')}):\n"
                    f"{result['transcript']}\n"
                )
            if result.get("record_saved"):
                result_text += f"\n✅ Record saved: `{result['record_path']}`\n"
        else:
            result_text += f"❌ {result.get('error', 'Processing failed')}\n"
            if result.get("note"):
                result_text += f"ℹ️ {result['note']}\n"
        return result_text

    # ── Prompts ────────────────────────────────────────────
    def kb_help() -> str:
        """Get help with using the knowledge base tools.

        Explains available tools, search, file reading and JSON querying.
        """
        return (
            "I need help using the knowledge base MCP server. Please explain:\n\n"
            "1. What tools are available\n"
            "2. How to search for information\n"
            "3. How to read files\n"
            "4. How to query JSON data\n\n"
            "Be concise and provide examples."
        )

    def kb_analyze_file(file_path: str) -> str:
        """Analyze a knowledge base file and provide insights.

        Args:
            file_path: Path to the file to analyze.
        """
        return (
            f"Please analyze the knowledge base file at '{file_path}'. "
            f"Provide a summary of its contents and key information."
        )

    server.add_prompt(
        Prompt.from_function(
            kb_help,
            name="kb_help",
            description="Get help with using the knowledge base tools",
        )
    )
    server.add_prompt(
        Prompt.from_function(
            kb_analyze_file,
            name="kb_analyze_file",
            description="Analyze a knowledge base file and provide insights",
        )
    )

    return server


def serve_kb_server(config: KnowledgeBaseConfig):
    """Run the MCP knowledge base server over stdio transport."""
    create_kb_server(config).run("stdio")


def serve_kb_server_sse(config: KnowledgeBaseConfig, host: str = "0.0.0.0", port: int = 8000):
    """Run the MCP knowledge base server over SSE transport.

    Exposes two endpoints:
      - GET  /sse        : SSE event stream for clients
      - POST /messages/  : client message ingestion
    """
    create_kb_server(config).run("sse", host=host, port=port)


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
        try:
            serve_kb_server_sse(config, port=port)
        except RuntimeError as e:
            click.echo(str(e), err=True)
            raise SystemExit(1)


if __name__ == "__main__":
    main()
