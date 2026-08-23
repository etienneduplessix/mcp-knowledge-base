# Coding Standards Specification

> **Project:** 项目知识库 / MCP Knowledge Base Server
> **Language:** Python
> **Version:** 1.0.0
> **Author:** Development Team
> **Created:** 2026-08-23 11:33:05

---

## 1. Language Conventions

### 1.1 Version

Specify the Python version and language level in use.

### 1.2 Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) / official Python style guide
- Line length: **100 characters** maximum
- Indentation: **4 spaces** (no tabs)
- File encoding: **UTF-8**

### 1.3 Type Hints

- Use type hints for all function signatures and public APIs
- Use `Optional[T]` for nullable values
- Use `Protocol` for structural subtyping

---

## 2. Naming Conventions

| Category | Convention | Example |
|----------|-----------|---------|
| Classes | PascalCase | `UserService` |
| Functions / Methods | snake_case | `get_user_by_id` |
| Variables | snake_case | `user_name` |
| Constants | UPPER_CASE | `MAX_RETRY_COUNT` |
| Private attributes | `_` prefix | `_internal_cache` |
| Protected attributes | `_` prefix | `_helper_method` |
| Modules | snake_case | `user_service.py` |
| Packages | lowercase | `services/` |

---

## 3. Project Structure

```
project_root/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── api/                 # API layer
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── core/                # Core business logic
│   │   ├── __init__.py
│   │   └── service.py
│   ├── models/              # Data models
│   │   ├── __init__.py
│   │   └── entities.py
│   ├── repository/          # Data access layer
│   │   ├── __init__.py
│   │   └── database.py
│   └── utils/               # Utilities
│       ├── __init__.py
│       └── helpers.py
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_api/
│   └── test_core/
├── docs/                    # Documentation
├── scripts/                 # Build & deployment scripts
├── pyproject.toml           # Project config
├── requirements.txt         # Dependencies
└── README.md
```

---

## 4. Documentation Standards

### 4.1 Docstrings

Use **Google-style** docstrings:

```python
def fetch_user(user_id: int) -> User | None:
    """Retrieve a user by their ID.

    Args:
        user_id: The unique identifier for the user.

    Returns:
        The User object if found, None otherwise.

    Raises:
        ConnectionError: If the database cannot be reached.
    """
    ...
```

### 4.2 Inline Comments

- Comment **why**, not **what** — the code should be self-explanatory
- Use `# TODO:`, `# FIXME:`, `# HACK:` annotations with ticket references

---

## 5. Error Handling

- Use specific exception types (avoid bare `except:`)
- Always use context managers (`with` statement) for resource management
- Log errors with appropriate severity levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- Use structured logging with correlation IDs for distributed tracing

---

## 6. Testing Standards

- **Framework:** pytest
- **Coverage Target:** >= 80%
- **Test Types:**
  - **Unit tests:** Test individual functions/classes in isolation
  - **Integration tests:** Test module interactions
  - **End-to-end tests:** Test full user flows
- **Test file naming:** `test_<module_name>.py`
- **Test class naming:** `Test<ClassName>`
- **Test function naming:** `test_<scenario>_<expected_behavior>`

---

## 7. Git Workflow

### 7.1 Branch Strategy (GitFlow / Trunk-based)

- `main` — production-ready code
- `develop` — integration branch
- `feature/*` — feature branches
- `bugfix/*` — bug fix branches
- `release/*` — release preparation

### 7.2 Commit Message Convention (Conventional Commits)

```
<type>(<scope>): <short summary>

[optional body]

[optional footer]
```

**Types:** `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`

### 7.3 Code Review Checklist

- [ ] Code is clean and readable
- [ ] Tests are included and passing
- [ ] Type hints are correct
- [ ] Documentation is updated
- [ ] No security vulnerabilities introduced

---

## 8. Performance Guidelines

- Prefer lazy evaluation and generators for large data sets
- Use connection pooling for database access
- Implement caching for expensive operations
- Use async/await for I/O-bound operations
- Profile before optimizing — measure, then improve

---

## 9. Security Guidelines

- Validate and sanitise all external input
- Use parameterised queries to prevent SQL injection
- Never log sensitive data (passwords, tokens, PII)
- Keep dependencies updated with `pip-audit` or similar
- Follow the principle of least privilege
