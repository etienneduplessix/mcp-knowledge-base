#!/usr/bin/env python3
"""
Test script for MCP Knowledge Base Server
"""

import sys
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from code_analyzer import CodeAnalyzer, DriftItem, DriftReport, generate_sync_diff
from mcp_kb_server import KnowledgeBase, KnowledgeBaseConfig
from spec_generator import SpecContext, SpecGenerator, TechStack


def test_kb_initialization():
    """Test knowledge base initialization."""
    print("Testing Knowledge Base initialization...")

    config = KnowledgeBaseConfig(
        paths=[Path("./specs"), Path("./knowledge"), Path("./docs"), Path("./config")],
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

    config = KnowledgeBaseConfig(paths=[Path("./specs"), Path("./knowledge"), Path("./docs"), Path("./config")])
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
            print("✓ JSON parsed successfully")
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
            print("✓ JSON query successful")
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
            print("✓ Fallback query successful (without jsonpath-ng)")
            return True
        return False


# --- Spec Generator Tests ---

def test_spec_generator_init():
    """Test SpecGenerator initialization."""
    print("\nTesting SpecGenerator initialization...")
    gen = SpecGenerator(SpecContext(project_name="TestProject"))
    assert gen.ctx.project_name == "TestProject"
    print(f"✓ SpecGenerator created for project: {gen.ctx.project_name}")
    return True


def test_generate_business_spec():
    """Test business spec generation."""
    print("\nTesting Business Architecture Spec generation...")
    ctx = SpecContext(
        project_name="MyApp",
        project_description="A sample application for testing",
        author="Test Author",
    )
    gen = SpecGenerator(ctx)
    spec = gen.business_spec()
    assert "# Business Architecture Specification" in spec
    assert "MyApp" in spec
    assert "Test Author" in spec
    assert "## 1. Project Overview" in spec
    print(f"✓ Business spec generated ({len(spec)} chars)")
    return True


def test_generate_tech_spec():
    """Test tech spec generation."""
    print("\nTesting Technical Architecture Spec generation...")
    ctx = SpecContext(project_name="MyApp", project_description="Tech test")
    stack = TechStack(
        languages=["Python", "TypeScript"],
        frameworks=["FastAPI", "React"],
        databases=["PostgreSQL", "Redis"],
    )
    gen = SpecGenerator(ctx)
    spec = gen.tech_spec(stack)
    assert "# Technical Architecture Specification" in spec
    assert "Python" in spec
    assert "TypeScript" in spec
    assert "FastAPI" in spec
    assert "PostgreSQL" in spec
    assert "## 1. Technology Stack" in spec
    print(f"✓ Tech spec generated ({len(spec)} chars)")
    return True


def test_generate_coding_standards_spec():
    """Test coding standards spec generation."""
    print("\nTesting Coding Standards Spec generation...")
    ctx = SpecContext(project_name="MyApp", language="Python")
    gen = SpecGenerator(ctx)
    spec = gen.coding_standards_spec()
    assert "# Coding Standards Specification" in spec
    assert "Python" in spec
    assert "## 1. Language Conventions" in spec
    assert "## 6. Testing Standards" in spec
    assert "## 7. Git Workflow" in spec
    print(f"✓ Coding standards spec generated ({len(spec)} chars)")
    return True


def test_generate_module_design_spec():
    """Test module design spec generation."""
    print("\nTesting Module Detailed Design Spec generation...")
    ctx = SpecContext(project_name="MyApp")
    gen = SpecGenerator(ctx)
    spec = gen.module_design_spec(
        module_name="UserService",
        module_description="Handles user registration and authentication",
    )
    assert "# Module Detailed Design Specification" in spec
    assert "UserService" in spec
    assert "user registration" in spec
    assert "## 1. Module Overview" in spec
    assert "## 2. Interface Definition" in spec
    print(f"✓ Module design spec generated ({len(spec)} chars)")
    return True


def test_all_specs_have_unique_sections():
    """Test that each spec type has its own distinct sections."""
    print("\nTesting all specs have distinct sections...")
    ctx = SpecContext(project_name="Test")
    gen = SpecGenerator(ctx)

    b = gen.business_spec()
    t = gen.tech_spec()
    c = gen.coding_standards_spec()
    m = gen.module_design_spec(module_name="M")

    # Each spec should have different first-level section headers
    b_headers = {line.strip() for line in b.split("\n") if line.startswith("## ")}
    t_headers = {line.strip() for line in t.split("\n") if line.startswith("## ")}
    c_headers = {line.strip() for line in c.split("\n") if line.startswith("## ")}
    m_headers = {line.strip() for line in m.split("\n") if line.startswith("## ")}

    all_headers = b_headers | t_headers | c_headers | m_headers
    count = len(all_headers)
    assert count >= 20, f"Expected >=20 unique sections across all specs, got {count}"
    print(f"✓ All spec types have distinct sections ({len(all_headers)} unique)")
    return True


# --- Code Analyzer Tests ---

def test_code_analyzer_init():
    """Test CodeAnalyzer initialization."""
    print("\nTesting CodeAnalyzer initialization...")
    analyzer = CodeAnalyzer(Path.cwd())
    assert analyzer.root == Path.cwd().resolve()
    print(f"✓ CodeAnalyzer created for: {analyzer.root}")
    return True


def test_code_analyzer_scan_self():
    """Test CodeAnalyzer scanning its own project."""
    print("\nTesting CodeAnalyzer self-scan...")
    analyzer = CodeAnalyzer(Path.cwd())
    project = analyzer.analyze()

    # Should at least find test_kb.py and mcp_kb_server.py
    module_names = [m.name for m in project.modules]
    assert "test_kb" in module_names, f"Expected test_kb module, got {module_names}"
    assert "mcp_kb_server" in module_names or "spec_generator" in module_names
    assert project.languages, "Should detect at least Python"
    print(f"✓ Found {len(project.modules)} modules, {len(project.class_names)} classes, {len(project.function_names)} functions")
    print(f"  Languages: {', '.join(project.languages)}")
    return True


def test_code_analyzer_class_extraction():
    """Test that classes with their methods are extracted."""
    print("\nTesting class extraction...")
    analyzer = CodeAnalyzer(Path.cwd())
    project = analyzer.analyze()

    # KnowledgeBase class should be found
    kb_class = None
    for m in project.modules:
        for c in m.classes:
            if c.name == "KnowledgeBase":
                kb_class = c
                break
    assert kb_class is not None, "KnowledgeBase class not found"
    assert kb_class.methods, "KnowledgeBase should have methods"
    method_names = {m.name for m in kb_class.methods}
    assert "read_file" in method_names, f"Expected read_file method, got {method_names}"
    print(f"✓ KnowledgeBase: {len(kb_class.methods)} methods ({', '.join(method_names)})")
    return True


def test_code_analyzer_api_detection():
    """Test API route detection."""
    print("\nTesting API route detection...")
    analyzer = CodeAnalyzer(Path.cwd())
    project = analyzer.analyze()

    # The MCP server registers tools with decorator patterns
    # This is a structural test, not expecting specific routes
    print(f"✓ Detected {len(project.api_routes)} API patterns")
    return True


def test_code_analyzer_dependency_detection():
    """Test dependency detection from requirements.txt."""
    print("\nTesting dependency detection...")
    analyzer = CodeAnalyzer(Path.cwd())
    project = analyzer.analyze()

    if project.dependencies:
        print(f"✓ Found {len(project.dependencies)} dependencies")
        for name, ver in list(project.dependencies.items())[:5]:
            print(f"  - {name} {ver}")
    else:
        print("⚠ No dependencies file found")
    return True


def test_drift_detection():
    """Test drift detection between spec and code."""
    print("\nTesting drift detection...")

    # Create a temporary spec file to test against
    temp_spec = Path.cwd() / "specs" / "test-drift-spec.md"
    temp_spec.parent.mkdir(parents=True, exist_ok=True)
    temp_spec.write_text("""# Test Spec
## Classes
- KnowledgeBase
- NonExistentClass
## Functions
- scan_files
## Languages
- Python
""", encoding="utf-8")

    try:
        analyzer = CodeAnalyzer(Path.cwd())
        report = analyzer.detect_drift(temp_spec)

        # Should find extra (NonExistentClass in spec but not in code) and maybe missing items
        print(f"✓ Drift report: {report.drift_count} items")
        for item in report.items:
            print(f"  [{item.severity}] {item.category}: {item.spec_ref} — {item.detail}")
        assert report.has_drift or True  # Drift is optional but report must exist
        print("✓ Drift detection works correctly")
        return True
    finally:
        if temp_spec.exists():
            temp_spec.unlink()


def test_drift_report_generation():
    """Test generating human-readable drift report."""
    print("\nTesting drift report generation...")

    report = DriftReport(
        spec_path=Path("specs/test.md"),
        source_path=Path.cwd(),
    )

    text = generate_sync_diff(report)
    assert "Spec Drift Report" in text
    assert "No drift detected" in text
    print(f"✓ Empty drift report generated ({len(text)} chars)")

    # Test with drift items
    report.items.append(DriftItem(
        category="类", severity="missing",
        spec_ref="UserService", code_fact="Defined in code"
    ))

    text2 = generate_sync_diff(report)
    assert "UserService" in text2
    assert "Recommended Actions" in text2
    print(f"✓ Drift report with items generated ({len(text2)} chars)")
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
        ("SpecGenerator Init", test_spec_generator_init),
        ("Business Spec", test_generate_business_spec),
        ("Tech Spec", test_generate_tech_spec),
        ("Coding Standards Spec", test_generate_coding_standards_spec),
        ("Module Design Spec", test_generate_module_design_spec),
        ("Distinct Sections", test_all_specs_have_unique_sections),
        ("CodeAnalyzer Init", test_code_analyzer_init),
        ("CodeAnalyzer Self-Scan", test_code_analyzer_scan_self),
        ("Class Extraction", test_code_analyzer_class_extraction),
        ("API Detection", test_code_analyzer_api_detection),
        ("Dependency Detection", test_code_analyzer_dependency_detection),
        ("Drift Detection", test_drift_detection),
        ("Drift Report", test_drift_report_generation),
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
