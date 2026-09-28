#!/usr/bin/env python3
"""
MCP Knowledge Base Server

A custom MCP server that provides tools for reading, searching, and querying
markdown and JSON files as a knowledge base for coding agents.
"""

import fnmatch
import functools
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from mcp.server import MCPServer
from mcp.server.mcpserver.prompts import Prompt
from mcp.types import Resource

from code_analyzer import CodeAnalyzer, generate_sync_diff
from spec_generator import SpecContext, SpecGenerator, TechStack


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

    @server.add_tool
    @_safe_tool
    def kb_generate_business_spec(
        project_name: str,
        project_description: str = "",
        author: str = "",
        version: str = "1.0.0",
        file_path: str = "",
    ) -> str:
        """Generate a Business Architecture Specification.

        Args:
            project_name: Name of the project.
            project_description: Brief description of the project.
            author: Author name.
            version: Project version.
            file_path: Optional: save spec to this file.
        """
        ctx = SpecContext(
            project_name=project_name,
            project_description=project_description,
            author=author,
            version=version,
        )
        gen = SpecGenerator(ctx)
        spec = gen.business_spec()
        if file_path:
            kb.write_file(file_path, spec)
            return f"# Business Architecture Spec Saved\n\n**File:** {file_path}\n\n{spec}"
        return spec

    @server.add_tool
    @_safe_tool
    def kb_generate_tech_spec(
        project_name: str,
        project_description: str = "",
        author: str = "",
        version: str = "1.0.0",
        languages: List[str] = None,
        frameworks: List[str] = None,
        databases: List[str] = None,
        file_path: str = "",
    ) -> str:
        """Generate a Technical Architecture Specification.

        Args:
            project_name: Name of the project.
            project_description: Brief project description.
            author: Author name.
            version: Project version.
            languages: Programming languages used.
            frameworks: Frameworks and libraries.
            databases: Databases used.
            file_path: Optional: save spec to this file.
        """
        ctx = SpecContext(
            project_name=project_name,
            project_description=project_description,
            author=author,
            version=version,
        )
        stack = TechStack(
            languages=languages or ["Python"],
            frameworks=frameworks or [],
            databases=databases or [],
        )
        gen = SpecGenerator(ctx)
        spec = gen.tech_spec(stack)
        if file_path:
            kb.write_file(file_path, spec)
            return f"# Technical Architecture Spec Saved\n\n**File:** {file_path}\n\n{spec}"
        return spec

    @server.add_tool
    @_safe_tool
    def kb_generate_coding_standards_spec(
        project_name: str,
        language: str = "Python",
        author: str = "",
        version: str = "1.0.0",
        file_path: str = "",
    ) -> str:
        """Generate a Coding Standards Specification.

        Args:
            project_name: Name of the project.
            language: Primary programming language.
            author: Author name.
            version: Project version.
            file_path: Optional: save spec to this file.
        """
        ctx = SpecContext(
            project_name=project_name,
            language=language,
            author=author,
            version=version,
        )
        gen = SpecGenerator(ctx)
        spec = gen.coding_standards_spec()
        if file_path:
            kb.write_file(file_path, spec)
            return f"# Coding Standards Spec Saved\n\n**File:** {file_path}\n\n{spec}"
        return spec

    @server.add_tool
    @_safe_tool
    def kb_generate_module_design_spec(
        project_name: str,
        module_name: str,
        module_description: str = "",
        author: str = "",
        version: str = "1.0.0",
        file_path: str = "",
    ) -> str:
        """Generate a Module Detailed Design Specification.

        Args:
            project_name: Name of the project.
            module_name: Name of the module being designed.
            module_description: Description of the module's purpose.
            author: Author name.
            version: Project version.
            file_path: Optional: save spec to this file.
        """
        ctx = SpecContext(
            project_name=project_name,
            author=author,
            version=version,
        )
        gen = SpecGenerator(ctx)
        spec = gen.module_design_spec(
            module_name=module_name,
            module_description=module_description,
        )
        if file_path:
            kb.write_file(file_path, spec)
            return f"# Module Design Spec Saved\n\n**File:** {file_path}\n\n{spec}"
        return spec

    @server.add_tool
    @_safe_tool
    def kb_analyze_code(source_path: str) -> str:
        """Analyze source code and extract project structure.

        Args:
            source_path: Path to the source code directory to analyze.
        """
        source = Path(source_path)
        if not source.exists():
            return f"Error: Source path not found: {source}"

        analyzer = CodeAnalyzer(source)
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

        return result_text

    @server.add_tool
    @_safe_tool
    def kb_check_spec_drift(spec_path: str, source_path: str) -> str:
        """Check spec drift: compare a spec document against source code.

        Args:
            spec_path: Path to the spec markdown file.
            source_path: Path to the source code directory.
        """
        spec = Path(spec_path)
        source = Path(source_path)
        if not spec.exists():
            return f"Error: Spec file not found: {spec}"
        if not source.exists():
            return f"Error: Source path not found: {source}"

        analyzer = CodeAnalyzer(source)
        report = analyzer.detect_drift(spec)
        return generate_sync_diff(report)

    @server.add_tool
    @_safe_tool
    def kb_sync_spec_from_code(spec_path: str, source_path: str) -> str:
        """Generate a drift report to sync a spec with actual code.

        Args:
            spec_path: Path to the spec markdown file to sync.
            source_path: Path to the source code directory.
        """
        spec = Path(spec_path)
        source = Path(source_path)
        if not spec.exists():
            return f"Error: Spec file not found: {spec}"
        if not source.exists():
            return f"Error: Source path not found: {source}"

        analyzer = CodeAnalyzer(source)
        report = analyzer.detect_drift(spec)

        result_text = "# Spec Sync from Code\n\n"
        result_text += f"**Spec:** {report.spec_path}\n"
        result_text += f"**Code:** {report.source_path}\n"
        result_text += f"**Drift Items:** {report.drift_count}\n\n"

        if not report.items:
            result_text += "✅ No drift detected — spec is up to date.\n"
            return result_text

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
    path = ()
    if os.environ.get("KB_PATHS"):
        paths = [Path(p.strip()).resolve() for p in os.environ["KB_PATHS"].split(",")]
    else:
        paths = [Path("./specs").resolve(), Path("./knowledge").resolve(), Path("./docs").resolve()]

    for p in paths:
        if not p.exists():
            # stderr: stdout is the stdio JSON-RPC channel and must stay clean
            print(f"Warning: Path does not exist: {p}", file=sys.stderr)

    config = KnowledgeBaseConfig(paths=paths)
    serve_kb_server(config)


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
            # stderr: stdout is the stdio JSON-RPC channel and must stay clean
            print(f"Warning: Path does not exist: {p}", file=sys.stderr)

    config = KnowledgeBaseConfig(paths=paths)

    if transport == "stdio":
        serve_kb_server(config)
    else:
        try:
            serve_kb_server_sse(config, port=port)
        except RuntimeError as e:
            click.echo(str(e), err=True)
            raise SystemExit(1)


if __name__ == "__main__":
    cli()
