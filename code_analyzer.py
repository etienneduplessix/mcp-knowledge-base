#!/usr/bin/env python3
"""Code analysis module for MCP Knowledge Base Server.

Analyses source code and compares it against spec documents to detect drift,
enabling reverse-sync from code back to specs.
"""

import ast
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ParamDef:
    name: str
    type_hint: str = ""
    default_value: str = ""


@dataclass
class FunctionDef:
    name: str
    params: list[ParamDef] = field(default_factory=list)
    return_type: str = ""
    decorators: list[str] = field(default_factory=list)
    docstring: str = ""
    is_async: bool = False


@dataclass
class ClassDef:
    name: str
    bases: list[str] = field(default_factory=list)
    methods: list[FunctionDef] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    docstring: str = ""


@dataclass
class SourceModule:
    path: Path
    name: str
    language: str
    classes: list[ClassDef] = field(default_factory=list)
    functions: list[FunctionDef] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    docstring: str = ""


@dataclass
class APIRoute:
    method: str
    path: str
    handler: str
    module: str = ""


@dataclass
class DataModelField:
    name: str
    type_hint: str = ""
    default: str = ""


@dataclass
class DataModel:
    name: str
    fields: list[DataModelField] = field(default_factory=list)
    table_name: str = ""
    source_file: str = ""


@dataclass
class ProjectStructure:
    root: Path
    source_dirs: list[str] = field(default_factory=list)
    modules: list[SourceModule] = field(default_factory=list)
    config_files: dict[str, dict] = field(default_factory=dict)
    api_routes: list[APIRoute] = field(default_factory=list)
    data_models: list[DataModel] = field(default_factory=list)
    dependencies: dict[str, str] = field(default_factory=dict)
    test_files: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)


@dataclass
class DriftItem:
    category: str
    severity: str  # missing / changed / extra
    spec_ref: str
    code_fact: str
    detail: str = ""


@dataclass
class DriftReport:
    spec_path: Path
    source_path: Path
    items: list[DriftItem] = field(default_factory=list)
    source_summary: str = ""
    spec_summary: str = ""

    @property
    def drift_count(self) -> int:
        return len(self.items)

    @property
    def has_drift(self) -> bool:
        return len(self.items) > 0


# ── AST-based Python parser ──────────────────────────────────

_PYTHON_TYPING_NAMES = {"str", "int", "float", "bool", "list", "dict", "tuple",
                        "set", "None", "Any", "Optional", "Union", "Callable",
                        "Type", "Sequence", "Mapping", "Iterable", "Iterator"}


def _parse_ast_node(node) -> str:
    """Convert an AST type annotation node back to a readable string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Subscript):
        value = _parse_ast_node(node.value)
        slice_val = _parse_ast_node(node.slice)
        return f"{value}[{slice_val}]"
    if isinstance(node, ast.Attribute):
        return f"{_parse_ast_node(node.value)}.{node.attr}"
    if isinstance(node, ast.Tuple):
        return ", ".join(_parse_ast_node(e) for e in node.elts)
    if isinstance(node, ast.Index):
        return _parse_ast_node(node.value)
    return ""


def _parse_param(arg: ast.arg, defaults: list, idx: int) -> ParamDef:
    type_hint = _parse_ast_node(arg.annotation) if arg.annotation else ""
    default = ""
    if defaults:
        default_idx = idx - (len(arg.annotation) if hasattr(arg, 'annotation') and arg.annotation else 0)
    # simpler approach
    return ParamDef(name=arg.arg, type_hint=type_hint)


def _parse_python_file(filepath: Path) -> Optional[SourceModule]:
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except Exception:
        return None

    module = SourceModule(
        path=filepath,
        name=filepath.stem,
        language="Python",
        docstring=ast.get_docstring(tree) or "",
    )

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module.imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module.imports.append(node.module)
        elif isinstance(node, ast.ClassDef):
            cls = ClassDef(
                name=node.name,
                bases=[_parse_ast_node(b) for b in node.bases],
                decorators=[d.id for d in node.decorator_list if isinstance(d, ast.Name)],
                docstring=ast.get_docstring(node) or "",
            )
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fn = _parse_function(item)
                    cls.methods.append(fn)
            module.classes.append(cls)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fn = _parse_function(node)
            module.functions.append(fn)

    return module


def _parse_function(node) -> FunctionDef:
    fn = FunctionDef(
        name=node.name,
        decorators=[d.id for d in node.decorator_list if isinstance(d, ast.Name)],
        docstring=ast.get_docstring(node) or "",
        is_async=isinstance(node, ast.AsyncFunctionDef),
    )

    # Extract return type
    if node.returns:
        fn.return_type = _parse_ast_node(node.returns)

    # Extract parameters
    defaults = node.args.defaults or []
    default_offset = len(node.args.args) - len(defaults)

    for i, arg in enumerate(node.args.args):
        param = ParamDef(name=arg.arg)
        if arg.annotation:
            param.type_hint = _parse_ast_node(arg.annotation)
        default_idx = i - default_offset
        if 0 <= default_idx < len(defaults):
            try:
                param.default_value = ast.literal_eval(defaults[default_idx])
            except Exception:
                param.default_value = "..."
        fn.params.append(param)

    return fn


# ── FastAPI/Flask route detection ────────────────────────────

_HTTP_METHODS = {"get", "post", "put", "delete", "patch", "options", "head"}

_FASTAPI_DECORATOR = re.compile(r"(app|router)\.(get|post|put|delete|patch)\(")


def _detect_api_routes(filepath: Path) -> list[APIRoute]:
    routes = []
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return routes

    # FastAPI-style: @app.get(...) / @router.post(...)
    for match in re.finditer(r'@\w+\.(get|post|put|delete|patch|options)\([\s\S]*?\)\s*\n\s*async?\s+def\s+(\w+)', content):
        method = match.group(1).upper()
        handler = match.group(2)

        # Try to extract path from the decorator
        path_match = re.search(r'["\']([^"\']+)["\']', match.group(0))
        path = path_match.group(1) if path_match else "/"

        routes.append(APIRoute(method=method, path=path, handler=handler, module=filepath.stem))

    # Flask-style: @app.route('/path', methods=['GET'])
    for match in re.finditer(r'@\w+\.route\([\s\S]*?\)', content):
        path_match = re.search(r'["\']([^"\']+)["\']', match.group(0))
        path = path_match.group(1) if path_match else "/"

        method_match = re.search(r"methods\s*=\s*\[?[\s\S]*?['\"](\w+)['\"]", match.group(0))
        method = method_match.group(1).upper() if method_match else "GET"

        # Find the function after the decorator
        func_match = re.search(r'def\s+(\w+)', content[match.end():])
        handler = func_match.group(1) if func_match else "unknown"

        routes.append(APIRoute(method=method, path=path, handler=handler, module=filepath.stem))

    return routes


# ── Dependency extraction ────────────────────────────────────

def _parse_requirements(path: Path) -> dict[str, str]:
    deps = {}
    try:
        content = path.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith(("#", "-i", "--")):
                continue
            m = re.match(r"^([\w\-.]+)\s*([><=!~]+.*)?$", line)
            if m:
                deps[m.group(1)] = (m.group(2) or "*").strip()
    except Exception:
        pass
    return deps


def _parse_pyproject_toml(path: Path) -> dict[str, str]:
    deps = {}
    try:
        content = path.read_text(encoding="utf-8")
        # Simple TOML parser for dependencies section
        in_deps = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and "dependencies" in stripped:
                in_deps = True
                continue
            if stripped.startswith("[") and in_deps:
                in_deps = False
            if in_deps and "=" in stripped:
                parts = stripped.split("=", 1)
                key = parts[0].strip().strip('"').strip("'")
                val = parts[1].strip().strip('"').strip("'")
                deps[key] = val
    except Exception:
        pass
    return deps


def _parse_package_json(path: Path) -> dict[str, str]:
    deps = {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        for key in ("dependencies", "devDependencies"):
            if key in data:
                deps.update(data[key])
    except Exception:
        pass
    return deps


def _detect_languages(root: Path) -> list[str]:
    exts = set()
    for f in root.rglob("*"):
        if f.is_file() and not f.name.startswith("."):
            exts.add(f.suffix)
    lang_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript/React",
        ".jsx": "JavaScript/React",
        ".java": "Java",
        ".go": "Go",
        ".rs": "Rust",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
        ".scala": "Scala",
        ".c": "C",
        ".cpp": "C++",
        ".h": "C/C++",
        ".hpp": "C++",
    }
    return sorted({lang_map[e] for e in exts if e in lang_map})


# ── Data model detection ─────────────────────────────────────

_DATACLASS_DECORATORS = {"dataclass", "dataclasses.dataclass"}


def _detect_data_models(source: SourceModule) -> list[DataModel]:
    models = []
    for cls in source.classes:
        decorators = set(cls.decorators)
        # Dataclass models
        is_model = bool(decorators & _DATACLASS_DECORATORS)
        # Pydantic models (BaseModel subclasses)
        is_pydantic = any("BaseModel" in b or "Model" in b for b in cls.bases)
        # SQLAlchemy models
        is_sa = any("Base" in b or "Model" in b for b in cls.bases)

        if is_model or is_pydantic or is_sa:
            model = DataModel(
                name=cls.name,
                source_file=str(source.path),
            )
            for method in cls.methods:
                if method.name == "__init__":
                    for p in method.params[1:]:  # skip self
                        model.fields.append(
                            DataModelField(name=p.name, type_hint=p.type_hint)
                        )
                if method.name == "__table__":  # SQLAlchemy
                    model.fields.append(DataModelField(name=method.name, type_hint="Table"))
            models.append(model)
    return models


# ── Main analyzer ────────────────────────────────────────────

class CodeAnalyzer:
    """Analyses source code and detects drift against spec documents."""

    def __init__(self, source_root: Path):
        self.root = source_root.resolve()

    def analyze(self) -> ProjectStructure:
        ps = ProjectStructure(root=self.root)

        # Find source directories
        for d in self.root.iterdir():
            if d.is_dir() and not d.name.startswith((".", "venv", "node_modules", "__pycache__", "env")):
                ps.source_dirs.append(d.name)

        # Detect languages
        ps.languages = _detect_languages(self.root)

        # Parse Python files
        for py_file in sorted(self.root.rglob("*.py")):
            if any(p.startswith(".") or p in ("venv", "node_modules", "__pycache__")
                   for p in py_file.relative_to(self.root).parts):
                continue
            module = _parse_python_file(py_file)
            if module:
                ps.modules.append(module)
                # Detect data models
                ps.data_models.extend(_detect_data_models(module))
                # Detect API routes
                ps.api_routes.extend(_detect_api_routes(py_file))

        # Detect test files
        for t in self.root.rglob("test_*.py"):
            ps.test_files.append(str(t))
        for t in self.root.rglob("*_test.py"):
            ps.test_files.append(str(t))

        # Parse config / dependency files
        for f in ("requirements.txt", "pyproject.toml", "package.json", "Pipfile", "Cargo.toml"):
            path = self.root / f
            if path.exists():
                if f == "requirements.txt":
                    ps.dependencies.update(_parse_requirements(path))
                elif f == "pyproject.toml":
                    ps.dependencies.update(_parse_pyproject_toml(path))
                elif f == "package.json":
                    ps.dependencies.update(_parse_package_json(path))

        # Parse config JSON files
        for cf in self.root.rglob("*.json"):
            if "node_modules" in str(cf):
                continue
            try:
                data = json.loads(cf.read_text(encoding="utf-8"))
                ps.config_files[str(cf.relative_to(self.root))] = data
            except Exception:
                pass

        return ps

    def detect_drift(self, spec_path: Path, source_path: Optional[Path] = None) -> DriftReport:
        """Compare a spec document against actual source code.

        This is a best-effort structural comparison. Some spec sections
        (business goals, stakeholder info) cannot be reverse-engineered.
        """
        src = source_path or self.root
        report = DriftReport(spec_path=spec_path.resolve(), source_path=src.resolve())

        if not spec_path.exists():
            report.items.append(DriftItem("文件", "missing", spec_path.name, "spec file not found"))
            return report

        try:
            spec_content = spec_path.read_text(encoding="utf-8")
        except Exception as e:
            report.items.append(DriftItem("文件", "changed", spec_path.name, f"cannot read: {e}"))
            return report

        code = self.analyze()

        # ── Drift checks ──

        # 1. Project name (from config files)
        project_name = ""
        for cf_name, cf_data in code.config_files.items():
            if isinstance(cf_data, dict):
                project_name = cf_data.get("project", {}).get("name", "") or cf_data.get("name", "")
        if project_name and project_name not in spec_content:
            report.items.append(DriftItem(
                "项目名称", "changed", "Project name in spec",
                f"Code says: {project_name}"
            ))

        # 2. Languages
        spec_langs = set()
        for m in re.finditer(r'(?:Languages?|语言)\s*[:：]\s*([^\n]+)', spec_content, re.IGNORECASE):
            for lang in m.group(1).split(","):
                spec_langs.add(lang.strip())
        code_langs = set(code.languages)
        added = code_langs - spec_langs
        removed = spec_langs - code_langs
        for lang in sorted(added):
            report.items.append(DriftItem("语言", "missing", f"Language: {lang}", "Found in code but not in spec"))
        for lang in sorted(removed):
            report.items.append(DriftItem("语言", "extra", f"Language: {lang}", "In spec but not found in code"))

        # 3. Modules / classes
        code_class_names = {c.name for m in code.modules for c in m.classes}
        spec_class_names = set(re.findall(r'(?:class|Class)\s+(\w+)', spec_content))

        for cn in sorted(code_class_names - spec_class_names):
            report.items.append(DriftItem("类", "missing", cn, "Defined in code, missing from spec"))
        for cn in sorted(spec_class_names - code_class_names):
            report.items.append(DriftItem("类", "extra", cn, "In spec but not found in code"))

        # 4. Functions / methods (top-level)
        code_fn_names = {f.name for m in code.modules for f in m.functions}
        spec_fn_names = set(re.findall(r'(?:def|function|async def)\s+(\w+)', spec_content))

        for fn in sorted(code_fn_names - spec_fn_names):
            report.items.append(DriftItem("函数", "missing", fn, "Defined in code, missing from spec"))
        for fn in sorted(spec_fn_names - code_class_names - code_fn_names):
            # Only flag if it looks like a code artifact, not a spec section
            if not fn.startswith(("test_", "_")):
                report.items.append(DriftItem("函数", "extra", fn, "In spec but not found in code"))

        # 5. API routes
        code_routes = {(r.method, r.path) for r in code.api_routes}
        spec_routes = set()
        for m in re.finditer(r'(GET|POST|PUT|DELETE|PATCH)\s+\|?\s*([/\w{}\-]+)', spec_content):
            spec_routes.add((m.group(1), m.group(2)))
        for m in re.finditer(r'(GET|POST|PUT|DELETE|PATCH)\s+([/\w{}\-]+)', spec_content):
            spec_routes.add((m.group(1), m.group(2)))

        added_routes = code_routes - spec_routes
        removed_routes = spec_routes - code_routes
        for method, path in sorted(added_routes):
            report.items.append(DriftItem("API", "missing", f"{method} {path}", "Found in code, missing from spec"))
        for method, path in sorted(removed_routes):
            report.items.append(DriftItem("API", "extra", f"{method} {path}", "In spec but not in code"))

        # 6. Dependencies
        code_deps = set(code.dependencies.keys())
        spec_deps = set(re.findall(r'([\w\-]+)\s*>?=?\s*\d+', spec_content))
        # Filter to likely package names
        known_pkgs = {d.lower() for d in code_deps}
        spec_pkg_mentions = {d.lower() for d in spec_deps if d.lower() in known_pkgs or len(d) > 2}

        added_deps = known_pkgs - spec_pkg_mentions
        for dep in sorted(added_deps):
            report.items.append(DriftItem("依赖", "missing", dep, "In requirements but not in spec"))

        # 7. Test coverage
        has_test_section = "testing" in spec_content.lower() or "test" in spec_content.lower()
        if code.test_files and not has_test_section:
            report.items.append(DriftItem("测试", "missing", "Test section", f"{len(code.test_files)} test files exist but no test section in spec"))

        # 8. Data models
        code_models = {m.name for m in code.data_models}
        spec_models = set(re.findall(r'(?:@dataclass|class|entity|Entity)\s+(\w+)', spec_content))
        for mn in sorted(code_models - spec_models):
            report.items.append(DriftItem("数据模型", "missing", mn, "Defined in code, missing from spec"))

        # Source summary
        module_summary = ", ".join(m.name for m in code.modules[:5])
        if len(code.modules) > 5:
            module_summary += f" ... and {len(code.modules) - 5} more"
        report.source_summary = (
            f"{len(code.modules)} modules, {len(code.class_names)} classes, "
            f"{len(code.function_names)} functions, {len(code.api_routes)} API routes, "
            f"{len(code.data_models)} data models"
        ) if hasattr(code, 'class_names') else f"{len(code.modules)} modules scanned"

        return report


# Helper properties added dynamically won't work, let's add them properly

def _class_names(ps: ProjectStructure) -> set[str]:
    return {c.name for m in ps.modules for c in m.classes}

def _function_names(ps: ProjectStructure) -> set[str]:
    return {f.name for m in ps.modules for f in m.functions}

ProjectStructure.class_names = property(lambda self: _class_names(self))
ProjectStructure.function_names = property(lambda self: _function_names(self))


# ── Spec sync generation ─────────────────────────────────────

def generate_sync_diff(report: DriftReport) -> str:
    """Generate a human-readable diff summary for spec updates."""
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "# Spec Drift Report",
        "",
        f"> **Spec:** {report.spec_path.name}",
        f"> **Source:** {report.source_path}",
        f"> **Generated:** {t}",
        f"> **Drift Items:** {report.drift_count}",
        "",
    ]

    if not report.items:
        lines.append("## ✅ No drift detected — spec is in sync with code.")
        return "\n".join(lines)

    # Group by severity
    for severity in ("missing", "changed", "extra"):
        items = [i for i in report.items if i.severity == severity]
        if not items:
            continue

        labels = {"missing": "🔴 Missing in spec", "changed": "🟡 Changed", "extra": "🟢 Extra in spec"}
        lines.append(f"## {labels[severity]}")
        lines.append("")
        lines.append("| Category | Item | Detail |")
        lines.append("|----------|------|--------|")
        for item in items:
            lines.append(f"| {item.category} | {item.spec_ref} | {item.detail} |")
        lines.append("")

    lines.append("## Recommended Actions")
    lines.append("")
    for item in report.items:
        if item.severity == "missing":
            lines.append(f"- **Add** to spec: `{item.spec_ref}` ({item.category})")
        elif item.severity == "extra":
            lines.append(f"- **Remove** from spec: `{item.spec_ref}` ({item.category})")
        elif item.severity == "changed":
            lines.append(f"- **Update** in spec: {item.spec_ref} → {item.detail}")

    return "\n".join(lines)
