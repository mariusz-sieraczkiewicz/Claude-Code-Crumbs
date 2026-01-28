# pyproject.toml Template - Python 3.12+

Complete configuration template for modern Python projects.

---

## Full Template

```toml
[project]
name = "my-package"
version = "0.1.0"
description = "A modern Python package"
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.12"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
keywords = ["python", "example"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Typing :: Typed",
]
dependencies = [
    "httpx>=0.27.0",
    "pydantic>=2.9.0",
]

[project.optional-dependencies]
dev = [
    "mypy>=1.13.0",
    "pytest>=8.3.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "pre-commit>=4.0.0",
]

[project.urls]
Homepage = "https://github.com/username/my-package"
Documentation = "https://my-package.readthedocs.io"
Repository = "https://github.com/username/my-package"
Changelog = "https://github.com/username/my-package/blob/main/CHANGELOG.md"

[project.scripts]
my-cli = "my_package.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/my_package"]


# ============================================================================
# RUFF - Linting and Formatting
# ============================================================================

[tool.ruff]
target-version = "py312"
line-length = 88
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # Pyflakes
    "I",      # isort
    "N",      # pep8-naming
    "UP",     # pyupgrade
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "SIM",    # flake8-simplify
    "ARG",    # flake8-unused-arguments
    "PTH",    # flake8-use-pathlib
    "RUF",    # Ruff-specific rules
    "PERF",   # Perflint
    "LOG",    # flake8-logging
    "G",      # flake8-logging-format
    "TRY",    # tryceratops
    "FLY",    # flynt
    "FURB",   # refurb
]
ignore = [
    "TRY003",  # Avoid long messages in exception class
]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = [
    "ARG001",  # Unused function argument (fixtures)
    "S101",    # Use of assert
]

[tool.ruff.lint.isort]
known-first-party = ["my_package"]
force-single-line = false
lines-after-imports = 2

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
docstring-code-format = true


# ============================================================================
# MYPY - Type Checking
# ============================================================================

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_ignores = true
warn_redundant_casts = true
warn_unused_configs = true
show_error_codes = true
show_column_numbers = true
pretty = true

# Per-module overrides
[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[[tool.mypy.overrides]]
module = [
    "some_untyped_library.*",
]
ignore_missing_imports = true


# ============================================================================
# PYTEST - Testing
# ============================================================================

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = [
    "-v",
    "--tb=short",
    "--strict-markers",
    "--strict-config",
]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
]
filterwarnings = [
    "error",
    "ignore::DeprecationWarning:some_library.*",
]


# ============================================================================
# COVERAGE
# ============================================================================

[tool.coverage.run]
source = ["src"]
branch = true
parallel = true
omit = [
    "src/my_package/__main__.py",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
    "@abstractmethod",
]
fail_under = 80
show_missing = true
skip_covered = true


# ============================================================================
# PYRIGHT (Alternative to mypy)
# ============================================================================

[tool.pyright]
pythonVersion = "3.12"
pythonPlatform = "All"
typeCheckingMode = "strict"
include = ["src"]
exclude = [
    "**/__pycache__",
    "**/node_modules",
    ".venv",
]
reportMissingImports = true
reportMissingTypeStubs = false
```

---

## Minimal Starter Template

For small projects or quick prototypes:

```toml
[project]
name = "my-package"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[project.optional-dependencies]
dev = ["mypy>=1.13.0", "pytest>=8.3.0", "ruff>=0.8.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "C4", "SIM", "RUF"]

[tool.mypy]
python_version = "3.12"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

---

## Tool Installation with uv

```bash
# Initialize new project
uv init my-project
cd my-project

# Add dependencies
uv add httpx pydantic

# Add dev dependencies
uv add --dev mypy pytest ruff pre-commit

# Sync environment
uv sync

# Run tools
uv run ruff check .
uv run ruff format .
uv run mypy src/
uv run pytest
```

---

## pre-commit Configuration

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-toml

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.9.0
          - types-requests
        args: [--strict]
```

Install hooks:
```bash
uv run pre-commit install
uv run pre-commit run --all-files
```

---

## GitHub Actions CI

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}

      - name: Install dependencies
        run: uv sync --all-extras

      - name: Lint with Ruff
        run: |
          uv run ruff check .
          uv run ruff format --check .

      - name: Type check with mypy
        run: uv run mypy src/

      - name: Test with pytest
        run: uv run pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
```
