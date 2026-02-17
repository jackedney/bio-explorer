---
name: style-python
description: Code style conventions for Python in this project
user-invocable: false
---

# Python Code Style

> Style guide: [PEP 8](https://peps.python.org/pep-0008/) — Style Guide for Python Code
> Tooling: ruff (linting + formatting), ty (type checking)

## Naming Conventions

```python
# Variables and functions — snake_case
taxon_key = 2435099
def fetch_occurrences(taxon_key: int) -> list[list[float]]: ...

# Classes — PascalCase
class GBIFClient: ...

# Constants — SCREAMING_SNAKE_CASE
MAX_OCCURRENCE_POINTS = 10_000
GBIF_BASE_URL = "https://api.gbif.org/v1"

# Private/internal — single leading underscore
_client: httpx.Client | None = None

# Modules — lowercase, short, no hyphens
# gbif.py, occurrence_service.py, not GBIF.py or occurrence-service.py
```

## Import and Module Structure

Order imports in three groups separated by blank lines (ruff enforces this via isort rules):

```python
# 1. Standard library
import json
import random
from typing import Any

# 2. Third-party
import httpx
from flask import Flask, abort, jsonify, render_template, request

# 3. Local/project
from bio_explorer.gbif import fetch_species_matches, fetch_occurrences
```

- One import per line for `from` imports; group multiple names with parentheses if needed.
- Never use wildcard imports (`from flask import *`).
- Prefer absolute imports over relative imports for clarity.

## Type Annotations

Annotate all function signatures. Use `from __future__ import annotations` only if needed for forward references.

```python
# Functions — always annotate parameters and return type
def sample_points(
    points: list[list[float]],
    max_count: int = 10_000,
) -> list[list[float]]:
    ...

# Use built-in generics (Python 3.10+), not typing module equivalents
def get_client() -> httpx.Client: ...        # not Client[Any]
params: dict[str, str | int] = {}            # not Dict, not Union

# Optional — prefer X | None over Optional[X]
def find_taxon(name: str) -> int | None: ...

# Return None explicitly for functions with no return value
def clear_cache() -> None: ...
```

ty enforces type correctness at CI. Do not silence errors with `type: ignore` without a comment explaining why.

## Documentation

Use Google-style docstrings for public functions and classes:

```python
def fetch_occurrences(taxon_key: int, limit: int = 10_000) -> list[list[float]]:
    """Fetch occurrence coordinates for a taxon from GBIF.

    Args:
        taxon_key: GBIF numeric taxon key.
        limit: Maximum number of coordinate pairs to return.

    Returns:
        List of [latitude, longitude] pairs, sampled to at most `limit` entries.

    Raises:
        GBIFError: If GBIF is unreachable or returns a non-2xx response.
    """
```

- Document public API functions, classes, and modules.
- One-line docstrings are fine for simple helpers.
- Skip docstrings on private helpers if the code is self-explanatory.
- Do not document parameters that are obvious from their type and name.

## Formatting Rules

Ruff auto-enforces these — run `ruff format` to apply:

- **Line length**: 88 characters (ruff default, matching Black)
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: double quotes for strings (`"text"`, not `'text'`)
- **Trailing commas**: added in multi-line collections and function signatures
- **Blank lines**: 2 between top-level definitions, 1 between methods

Manual rules ruff does not enforce:

- Use `_` as a throwaway variable name, not `dummy` or `unused`
- Prefer `f"..."` over `"..." .format(...)` for string interpolation
- Use numeric literals with underscores for readability: `10_000` not `10000`
- Avoid mutable default arguments (`def f(x=[])`) — use `None` and initialise inside
