#!/usr/bin/env python3
"""Spec generation module for MCP Knowledge Base Server.

Generates structured specification documents for spec-driven development:
- Business Architecture Spec
- Technical Architecture Spec
- Coding Standards Spec
- Module Detailed Design Spec
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


def _list_or_tbd(items: list[str]) -> str:
    return "\n".join(f"  - {item}" for item in items) if items else "  - (to be decided)"


@dataclass
class SpecContext:
    project_name: str
    project_description: str = ""
    language: str = "Python"
    version: str = "1.0.0"
    author: str = ""
    created_at: str = ""


@dataclass
class TechStack:
    languages: list[str] = field(default_factory=lambda: ["Python"])
    frameworks: list[str] = field(default_factory=list)
    databases: list[str] = field(default_factory=list)
    message_queue: list[str] = field(default_factory=list)
    cache: list[str] = field(default_factory=list)
    devops: list[str] = field(default_factory=list)
    monitoring: list[str] = field(default_factory=list)


def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_business_spec(ctx: SpecContext) -> str:
    t = _timestamp()
    a = ctx.author or ctx.project_name
    return f"""# Business Architecture Specification

> **Project:** {ctx.project_name}
> **Version:** {ctx.version}
> **Author:** {a}
> **Created:** {t}

---

## 1. Project Overview

{ctx.project_description}

### 1.1 Background

Describe the business background and motivation for this project.

### 1.2 Scope

Define the scope of this project — what is included and what is explicitly excluded.

### 1.3 Goals & Objectives

- **Goal 1:** ...
- **Goal 2:** ...
- **Goal 3:** ...

---

## 2. Business Domain Model

### 2.1 Core Entities

| Entity | Description | Key Attributes |
|--------|-------------|----------------|
| EntityA | ... | ... |
| EntityB | ... | ... |

### 2.2 Domain Relationships

Describe how domain entities relate to each other.

### 2.3 Bounded Contexts

List the bounded contexts and their responsibilities.

---

## 3. Core Business Processes

### 3.1 Process Flow

```mermaid
graph TD
    A[Start] --> B[Step 1]
    B --> C[Step 2]
    C --> D[End]
```

### 3.2 Business Rules

| Rule ID | Description | Priority |
|---------|-------------|----------|
| BR-001 | ... | High/Medium/Low |

---

## 4. Use Cases

| UC ID | Name | Actor | Description |
|-------|------|-------|-------------|
| UC-001 | ... | ... | ... |

---

## 5. Stakeholders

| Role | Responsibility | Concerns |
|------|---------------|----------|
| Product Owner | ... | ... |
| Developer | ... | ... |

---

## 6. Key Performance Indicators

| KPI | Description | Target |
|-----|-------------|--------|
| KPI-001 | ... | ... |

---

## 7. Constraints & Assumptions

- **Constraint 1:** ...
- **Assumption 1:** ...
"""


def generate_tech_spec(ctx: SpecContext, stack: Optional[TechStack] = None) -> str:
    t = _timestamp()
    a = ctx.author or ctx.project_name
    s = stack or TechStack()

    lang_list = "\n".join(f"  - {lang}" for lang in s.languages)
    fw_list = _list_or_tbd(s.frameworks)
    db_list = _list_or_tbd(s.databases)
    mq_list = _list_or_tbd(s.message_queue)
    cache_list = _list_or_tbd(s.cache)
    devops_list = _list_or_tbd(s.devops)
    mon_list = _list_or_tbd(s.monitoring)

    return f"""# Technical Architecture Specification

> **Project:** {ctx.project_name}
> **Version:** {ctx.version}
> **Author:** {a}
> **Created:** {t}

---

## 1. Technology Stack

### 1.1 Languages
{lang_list}

### 1.2 Frameworks & Libraries
{fw_list}

### 1.3 Database
{db_list}

### 1.4 Message Queue
{mq_list}

### 1.5 Cache
{cache_list}

### 1.6 DevOps & Infrastructure
{devops_list}

### 1.7 Monitoring & Observability
{mon_list}

---

## 2. System Architecture

### 2.1 Architecture Overview

Describe the system architecture (Monolithic / Microservices / Layered / Hexagonal, etc.).

```mermaid
graph TB
    subgraph Client Layer
        A[Web App]
        B[Mobile App]
    end
    subgraph API Layer
        C[API Gateway]
    end
    subgraph Service Layer
        D[Service A]
        E[Service B]
    end
    subgraph Data Layer
        F[(Database)]
        G[(Cache)]
    end
    A --> C
    B --> C
    C --> D
    C --> E
    D --> F
    D --> G
    E --> F
```

### 2.2 Module Breakdown

| Module | Responsibility | Dependencies |
|--------|---------------|-------------|
| Module A | ... | ... |
| Module B | ... | ... |

---

## 3. Data Architecture

### 3.1 Data Model

Describe the core data entities and their relationships.

### 3.2 Data Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Service
    participant DB
    Client->>API: Request
    API->>Service: Process
    Service->>DB: Query
    DB-->>Service: Result
    Service-->>API: Response
    API-->>Client: Response
```

---

## 4. API Design

### 4.1 RESTful APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/resource | List resources |
| POST | /api/v1/resource | Create resource |

### 4.2 Internal Interfaces

Describe inter-module communication interfaces.

---

## 5. Database Design

### 5.1 Schema

```sql
-- Core tables
CREATE TABLE example (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 5.2 Indexing Strategy

| Table | Index | Type | Rationale |
|-------|-------|------|-----------|
| ... | ... | B-tree | ... |

---

## 6. Security Architecture

- **Authentication:** ...
- **Authorization:** ...
- **Data Encryption:** ...
- **Network Security:** ...

---

## 7. Deployment Architecture

### 7.1 Environment Strategy

| Environment | Purpose | Configuration |
|-------------|---------|--------------|
| dev | Development | ... |
| staging | Testing | ... |
| production | Live | ... |

### 7.2 CI/CD Pipeline

Describe the build, test, and deployment pipeline.

---

## 8. Scalability & Performance

- **Horizontal Scaling:** ...
- **Vertical Scaling:** ...
- **Caching Strategy:** ...
- **Rate Limiting:** ...

---

## 9. Disaster Recovery & Backup

- **Backup Strategy:** ...
- **Recovery Point Objective (RPO):** ...
- **Recovery Time Objective (RTO):** ...
"""


def generate_coding_standards_spec(ctx: SpecContext) -> str:
    t = _timestamp()
    a = ctx.author or ctx.project_name
    lang = ctx.language
    return f"""# Coding Standards Specification

> **Project:** {ctx.project_name}
> **Language:** {lang}
> **Version:** {ctx.version}
> **Author:** {a}
> **Created:** {t}

---

## 1. Language Conventions

### 1.1 Version

Specify the {lang} version and language level in use.

### 1.2 Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) / official {lang} style guide
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
    \"\"\"Retrieve a user by their ID.

    Args:
        user_id: The unique identifier for the user.

    Returns:
        The User object if found, None otherwise.

    Raises:
        ConnectionError: If the database cannot be reached.
    \"\"\"
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
"""


def generate_module_design_spec(
    ctx: SpecContext, module_name: str = "", module_description: str = ""
) -> str:
    t = _timestamp()
    a = ctx.author or ctx.project_name
    mn = module_name or "<ModuleName>"
    md = module_description or "Describe the module's purpose and responsibilities."
    return f"""# Module Detailed Design Specification

> **Project:** {ctx.project_name}
> **Module:** {mn}
> **Version:** {ctx.version}
> **Author:** {a}
> **Created:** {t}

---

## 1. Module Overview

### 1.1 Purpose

{md}

### 1.2 Responsibilities

- Responsibility 1: ...
- Responsibility 2: ...
- Responsibility 3: ...

### 1.3 Scope

Define what this module does and explicitly what it does **not** do.

---

## 2. Interface Definition

### 2.1 Public API

| Method / Function | Signature | Description |
|-------------------|-----------|-------------|
| `func_a` | `(param1: str) -> Result` | ... |
| `func_b` | `(param2: int) -> None` | ... |

### 2.2 Events

| Event | Payload | Publisher | Subscriber |
|-------|---------|-----------|------------|
| `event_a` | `{...}` | Module A | Module B |

### 2.3 Configuration

```python
# Configuration keys for this module
MODULE_CONFIG = {{
    "setting_a": "default_value",
    "setting_b": 42,
}}
```

---

## 3. Data Structures

### 3.1 Core Data Models

```python
@dataclass
class CoreEntity:
    \"\"\"Description of this entity.\"\"\"
    id: str
    name: str
    created_at: datetime
```

### 3.2 Internal State

Describe the internal state this module maintains (if any).

---

## 4. Core Logic / Algorithms

### 4.1 Flowchart

```mermaid
flowchart TD
    A[Input] --> B{{Validation}}
    B -->|Valid| C[Process]
    B -->|Invalid| D[Return Error]
    C --> E[Output]
```

### 4.2 Pseudo-code / Key Algorithm

```
function handleRequest(input):
    1. validate input
    2. transform to internal model
    3. execute business rule
    4. persist result
    5. return response
```

### 4.3 Edge Cases

- Edge case 1: ...
- Edge case 2: ...
- Error scenario: ...

---

## 5. Dependencies

### 5.1 Internal Dependencies

| Module | Dependency Type | Description |
|--------|---------------|-------------|
| Module X | import / call | ... |

### 5.2 External Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| library-a | >=1.0 | ... |

---

## 6. Error Handling

| Error Condition | Error Type | Recovery Strategy |
|-----------------|-----------|-------------------|
| ... | `ValueError` | ... |

---

## 7. Testing Strategy

### 7.1 Unit Tests

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| `test_case_a` | ... | ... |

### 7.2 Integration Points

Describe how to test this module's integration with other modules.

### 7.3 Mocking Strategy

Describe what external dependencies should be mocked during testing.

---

## 8. Performance Considerations

- **Expected load:** ...
- **Critical path:** ...
- **Optimisation opportunities:** ...

---

## 9. Open Questions

- [ ] Question 1: ...
- [ ] Question 2: ...
"""


class SpecGenerator:
    """Generates structured specification documents."""

    def __init__(self, ctx: Optional[SpecContext] = None):
        self.ctx = ctx or SpecContext(project_name="Untitled")

    def set_context(self, ctx: SpecContext):
        self.ctx = ctx

    def business_spec(self) -> str:
        return generate_business_spec(self.ctx)

    def tech_spec(self, stack: Optional[TechStack] = None) -> str:
        return generate_tech_spec(self.ctx, stack)

    def coding_standards_spec(self) -> str:
        return generate_coding_standards_spec(self.ctx)

    def module_design_spec(self, module_name: str = "", module_description: str = "") -> str:
        return generate_module_design_spec(self.ctx, module_name, module_description)
