#!/usr/bin/env python3
"""
Test script for MCP Knowledge Base Server
"""

import asyncio
import sys
import tempfile
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_kb_server import KnowledgeBase, KnowledgeBaseConfig


def test_kb_initialization():
    """Test knowledge base initialization."""
    print("Testing Knowledge Base initialization...")

    config = KnowledgeBaseConfig(
        paths=[Path("./knowledge"), Path("./docs"), Path("./config")],
        file_extensions=[".md", ".json"],
    )

    kb = KnowledgeBase(config)
    files = kb.scan_files()

    print(f"✓ Found {len(files)} files in knowledge base")
    for f in files:
        print(f"  - {f.name}")

    return len(files) > 0


def test_read_file():
    """Test reading a file."""
    print("\nTesting file reading...")

    config = KnowledgeBaseConfig(paths=[Path("./knowledge"), Path("./docs"), Path("./config")])
    kb = KnowledgeBase(config)

    # Try to read a markdown file
    try:
        data = kb.read_file("knowledge/coding-standards.md")
        print(f"✓ Successfully read {data['name']}")
        print(f"  - Size: {data['size_bytes']} bytes")
        print(f"  - Extension: {data['extension']}")
        return True
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return False


def test_read_json():
    """Test reading a JSON file."""
    print("\nTesting JSON file reading...")

    config = KnowledgeBaseConfig(paths=[Path("./config")])
    kb = KnowledgeBase(config)

    try:
        data = kb.read_file("config/app-config.json")
        print(f"✓ Successfully read {data['name']}")
        if "parsed" in data:
            print(f"✓ JSON parsed successfully")
            print(f"  - Project name: {data['parsed'].get('project', {}).get('name', 'N/A')}")
            return True
        else:
            print("✗ JSON parsing failed")
            return False
    except Exception as e:
        print(f"✗ Error reading file: {e}")
        return False


def test_search():
    """Test searching files."""
    print("\nTesting search functionality...")

    config = KnowledgeBaseConfig(paths=[Path("./knowledge"), Path("./docs"), Path("./config")])
    kb = KnowledgeBase(config)

    results = kb.search("API")
    print(f"✓ Found {len(results)} file(s) containing 'API'")

    for r in results:
        print(f"  - {r['name']}: {r['matches_count']} match(es)")

    return len(results) > 0


def test_list_files():
    """Test listing files."""
    print("\nTesting file listing...")

    config = KnowledgeBaseConfig(paths=[Path("./knowledge"), Path("./docs"), Path("./config")])
    kb = KnowledgeBase(config)

    files = kb.list_files()
    print(f"✓ Listed {len(files)} files")

    # Test filtering by extension
    json_files = kb.list_files(extension=".json")
    print(f"✓ Found {len(json_files)} JSON files")

    md_files = kb.list_files(extension=".md")
    print(f"✓ Found {len(md_files)} Markdown files")

    return len(files) > 0


def test_query_json():
    """Test JSON querying."""
    print("\nTesting JSON querying...")

    config = KnowledgeBaseConfig(paths=[Path("./config")])
    kb = KnowledgeBase(config)

    try:
        # Test simple query
        result = kb.query_json("config/app-config.json", "$.project.name")
        if "result" in result or "matches" in result:
            print(f"✓ JSON query successful")
            if "matches" in result:
                print(f"  - Matches: {result['matches']}")
            elif "result" in result:
                print(f"  - Result: {result['result']}")
            return True
        else:
            print(f"✗ Query returned no results: {result}")
            return False
    except Exception as e:
        print(f"✗ Error querying JSON: {e}")
        # Try without jsonpath-ng
        result = kb.query_json("config/app-config.json")
        if "data" in result:
            print(f"✓ Fallback query successful (without jsonpath-ng)")
            return True
        return False


def test_get_file_info():
    """Test lightweight file metadata (no full content read)."""
    print("\nTesting file info...")

    config = KnowledgeBaseConfig(paths=[Path("./knowledge"), Path("./docs"), Path("./config")])
    kb = KnowledgeBase(config)

    try:
        info = kb.get_file_info("knowledge/coding-standards.md")
        print(f"✓ Got info for {info['name']}")
        print(f"  - Size: {info['size_bytes']} bytes")
        print(f"  - Type: {info['type']}")
        return info["type"] == "text_markdown" and info["size_bytes"] > 0
    except Exception as e:
        print(f"✗ Error getting file info: {e}")
        return False


def test_backup_restore():
    """Test automatic backups and restore for write operations."""
    print("\nTesting backup & restore...")

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        kb = KnowledgeBase(KnowledgeBaseConfig(paths=[base]))

        # Create a file
        kb.create_file("test.md", "# Original\nHello world")
        path = base / "test.md"

        # Overwrite -> backup should exist with previous content
        kb.write_file("test.md", "# Modified\nChanged content")
        bak = path.with_name(path.name + ".bak")
        assert bak.exists(), "Backup file not created"
        assert "Original" in bak.read_text(encoding="utf-8"), "Backup has wrong content"
        print(f"✓ Write created backup: {bak.name}")

        # Restore -> original content back
        kb.restore_from_backup("test.md")
        assert "Original" in path.read_text(encoding="utf-8")
        print("✓ Restore returned original content")

        # Delete -> still recoverable via backup
        kb.delete_file("test.md")
        assert not path.exists(), "File not deleted"
        assert bak.exists(), "Backup lost after delete"
        kb.restore_from_backup("test.md")
        assert path.exists(), "Restore after delete failed"
        print("✓ Delete + restore recovered deleted file")

        return True


def test_cache_invalidation():
    """Test that search reflects edits (index cache invalidation)."""
    print("\nTesting search cache invalidation...")

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        kb = KnowledgeBase(KnowledgeBaseConfig(paths=[base]))

        kb.create_file("test.md", "# Doc\nNo matching content here")
        assert kb.search("needle") == [], "Search should find nothing initially"

        # Edit the file to add the term
        kb.edit_file("test.md", "No matching content here", "needle found in content")
        results = kb.search("needle")
        assert len(results) == 1, "Search should find the edited file"
        assert results[0]["matches_count"] >= 1
        print(f"✓ Search reflected edit ({results[0]['matches_count']} match(es))")

        return True


def test_process_media():
    """Test media processing integration (unsupported/CLI guard cases)."""
    print("\nTesting media processing integration...")

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        kb = KnowledgeBase(KnowledgeBaseConfig(paths=[base]))

        # Unsupported extension -> structured error
        bad = base / "notes.txt"
        bad.write_text("hi", encoding="utf-8")
        result = kb.process_media(str(bad))
        assert result["success"] is False, "Unsupported type should fail"
        assert "error" in result
        print(f"✓ Unsupported type handled: {result['error']}")

        # Image without pytesseract -> graceful degradation message
        img = base / "photo.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
        result = kb.process_media(str(img))
        assert result["success"] is False
        assert "error" in result
        print(f"✓ Image processed with graceful degradation: {result['error']}")

        return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("MCP Knowledge Base Server - Test Suite")
    print("=" * 50)

    tests = [
        ("Initialization", test_kb_initialization),
        ("Read File", test_read_file),
        ("Read JSON", test_read_json),
        ("Search", test_search),
        ("List Files", test_list_files),
        ("Query JSON", test_query_json),
        ("Get File Info", test_get_file_info),
        ("Backup & Restore", test_backup_restore),
        ("Cache Invalidation", test_cache_invalidation),
        ("Media Processing", test_process_media),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
