---
name: python-modern-practices
description: |
  Modern Python 3.12+ programming guidelines with strict typing. Use when writing,
  reviewing, or refactoring Python code. Covers clean code fundamentals, imports,
  exception handling, logging, type hints (strict mode), project structure, and
  modern tooling (Ruff, mypy, uv). Invoke with /python-modern-practices.
---

# Python Modern Practices (3.12+)

Apply these rules to all Python code. Target Python 3.12+ with strict typing.

---

## 1. Clean Code Fundamentals

### Formatting
- Use 4-space indentation (never tabs)
- Maximum line length: 88 characters (Black/Ruff default)
- Use trailing commas in multi-line structures
- One blank line between functions, two between classes

### Naming Conventions
- `snake_case` for functions, methods, variables, modules
- `CamelCase` for classes
- `UPPER_CASE` for constants
- `_private` prefix for internal use
- Descriptive names: `user_count` not `n`, `calculate_total` not `calc`

### Function Design
- Maximum 20 lines per function
- Single responsibility: one function does one thing
- Maximum 4 parameters; use dataclass/TypedDict for more
- Use early returns to reduce nesting depth
- Keep nesting to maximum 3 levels

### String Formatting
- Use f-strings exclusively: `f"Hello {name}"`
- Never use `%` formatting or `.format()`
- For long f-strings, use parentheses:
  ```python
  message = (
      f"User {user.name} performed action {action} "
      f"at {timestamp.isoformat()}"
  )
  ```

### Comments and Documentation
- Write self-documenting code; minimize comments
- Use docstrings for public APIs only
- Comments explain "why", not "what"
- Remove commented-out code

---

## 2. Import Organization

### Import Order (with blank lines between groups)
1. Standard library imports
2. Third-party imports
3. Local application imports

### Import Rules
- Use absolute imports: `from mypackage.module import func`
- Never use `from x import *`
- Import modules, not individual items when possible
- Group related imports on single line if short

### Example
```python
import json
import logging
from collections.abc import Callable, Sequence
from pathlib import Path

import httpx
from pydantic import BaseModel

from myapp.core import settings
from myapp.models import User
```

### Tool Configuration
Configure Ruff to enforce import order in `pyproject.toml`:
```toml
[tool.ruff.lint.isort]
known-first-party = ["myapp"]
force-single-line = false
```

---

## 3. Exception Handling

### Tight Try Blocks
Wrap only the risky operation, not surrounding code:
```python
# GOOD
user_id = extract_user_id(request)
try:
    user = repository.get_user(user_id)
except UserNotFoundError:
    return None
return process_user(user)

# BAD - too broad
try:
    user_id = extract_user_id(request)
    user = repository.get_user(user_id)
    return process_user(user)
except UserNotFoundError:
    return None
```

### Specific Exceptions
- Always catch specific exceptions: `except ValueError as e:`
- Never use bare `except:` or `except Exception:`
- Let unexpected exceptions propagate

### Exception Chaining
Preserve original traceback with `from`:
```python
try:
    data = json.loads(raw_data)
except json.JSONDecodeError as e:
    raise ConfigurationError(f"Invalid config: {e}") from e
```

### Custom Domain Exceptions
Define exceptions for your domain:
```python
class AppError(Exception):
    """Base exception for application."""

class UserNotFoundError(AppError):
    """Raised when user does not exist."""

class ValidationError(AppError):
    """Raised when validation fails."""
```

### Cleanup with Context Managers
Use `with` for resource management:
```python
with Path("data.json").open() as f:
    data = json.load(f)
```

---

## 4. Logging

### Logger Setup
One logger per module at module level:
```python
import logging

logger = logging.getLogger(__name__)
```

### Never Print
- Never use `print()` in production code
- Use `logger.debug()` for development output
- Configure log level via environment

### Log Levels
| Level | Usage |
|-------|-------|
| DEBUG | Detailed diagnostic information |
| INFO | Confirm things work as expected |
| WARNING | Something unexpected but not error |
| ERROR | Serious problem, operation failed |
| CRITICAL | System-wide failure, shutdown |

### Include Context
Always include relevant context:
```python
logger.info("User created", extra={"user_id": user.id, "email": user.email})
logger.error("Payment failed", extra={"order_id": order_id, "amount": amount})
```

### Use exception() for Tracebacks
In except blocks, use `exception()` to include traceback:
```python
try:
    process_order(order)
except PaymentError:
    logger.exception("Payment processing failed for order %s", order.id)
    raise
```

### Structured Logging for Production
Use JSON logging in production:
```python
import structlog

logger = structlog.get_logger()
logger.info("request_processed", method="POST", path="/api/users", status=201)
```

---

## 5. Type Hints & Type Safety (Strict)

### All Functions Must Be Typed
Every function requires parameter types and return type:
```python
def calculate_total(items: list[CartItem], discount: Decimal) -> Decimal:
    ...

def find_user(user_id: int) -> User | None:
    ...
```

### Python 3.12+ Type Syntax
Use modern syntax without `typing` imports:
```python
# Union types
def parse(value: str | bytes) -> dict[str, Any]: ...

# Optional (use union with None)
def get_user(id: int) -> User | None: ...

# Generic type parameters (PEP 695)
def first[T](items: Sequence[T]) -> T: ...

# Type aliases (PEP 695)
type UserDict = dict[str, User]
type Handler[T] = Callable[[T], None]
```

### Built-in Generic Collections
Use native generics, never import from `typing`:
```python
# GOOD
def process(items: list[str], mapping: dict[str, int]) -> set[int]: ...

# BAD - legacy syntax
from typing import List, Dict, Set
def process(items: List[str], mapping: Dict[str, int]) -> Set[int]: ...
```

### No Any Type
`Any` is forbidden without explicit justification in a comment:
```python
# BAD
def process(data: Any) -> Any: ...

# GOOD - if truly needed, justify
def deserialize(data: bytes) -> object:  # Returns unknown structure
    ...
```

### Use TypedDict for Dictionaries
When dict structure is known:
```python
class UserPayload(TypedDict):
    name: str
    email: str
    age: int | None
```

### Use @override for Overridden Methods
PEP 698 - indicate method overrides explicitly:
```python
from typing import override

class Child(Parent):
    @override
    def process(self, data: bytes) -> str:
        ...
```

### Pydantic for External Data
Validate all external input with Pydantic:
```python
from pydantic import BaseModel, EmailStr

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    age: int = Field(ge=0, le=150)
```

### Type Checking Configuration
Mandatory in `pyproject.toml`:
```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_ignores = true
```

---

## 6. Project Structure

### Standard Layout
```
project-name/
├── src/
│   └── package_name/
│       ├── __init__.py
│       ├── core/
│       ├── models/
│       └── services/
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_*.py
├── pyproject.toml
├── README.md
└── LICENSE
```

### src/ Layout is Mandatory
- All package code under `src/package_name/`
- Prevents import confusion between installed and local
- Required for modern packaging

### Module Organization
- `__init__.py` exports public API only
- Keep modules focused: one domain concept per module
- Use `__all__` to define public exports

### Configuration Files
All configuration in `pyproject.toml`:
- Project metadata
- Dependencies
- Tool configuration (Ruff, mypy, pytest)

---

## 7. Modern Tooling (2025-2026)

### Ruff (Required)
Replaces flake8, isort, black, and more:
```toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM", "RUF"]
```

Run: `ruff check . && ruff format .`

### mypy --strict (Required)
Type checking in CI is mandatory:
```toml
[tool.mypy]
python_version = "3.12"
strict = true
```

Run: `mypy src/`

### pytest (Required)
Testing framework:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

### uv (Preferred)
Fast dependency management:
```bash
uv init
uv add httpx pydantic
uv sync
uv run pytest
```

### pre-commit (Recommended)
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies: [pydantic]
```

---

## 8. Quick Reference Checklists

### Before Writing Code
- [ ] Python 3.12+ target set in pyproject.toml
- [ ] src/ layout structure in place
- [ ] Ruff and mypy configured
- [ ] Logger set up (not print)

### Before Committing
- [ ] `ruff check . && ruff format .` passes
- [ ] `mypy src/` passes with --strict
- [ ] `pytest` passes
- [ ] No `print()` statements
- [ ] No `# type: ignore` without comment justification
- [ ] No `Any` types without justification

### When Handling Errors
- [ ] Try block wraps only risky operation
- [ ] Specific exception type caught
- [ ] Exception chained with `from` when re-raising
- [ ] `logger.exception()` used for logging errors
- [ ] Resources cleaned up with context manager

### When Writing Functions
- [ ] All parameters typed
- [ ] Return type specified
- [ ] Under 20 lines
- [ ] Single responsibility
- [ ] Max 4 parameters
- [ ] Early returns used
- [ ] Descriptive name

### When Creating Classes
- [ ] Use `@dataclass` for data containers
- [ ] Use Pydantic `BaseModel` for external data
- [ ] `@override` decorator on overridden methods
- [ ] Type hints on all attributes
- [ ] `__slots__` for performance-critical classes

---

## Reference Files

For detailed examples, see:
- `references/code-examples.md` - Complete code patterns
- `references/pyproject-template.md` - Full configuration template
- `references/anti-patterns.md` - BAD vs GOOD comparisons
