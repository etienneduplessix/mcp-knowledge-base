#!/usr/bin/env python3
"""
Test script for MCP Knowledge Base Server
"""

import asyncio
import sys
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
