---
name: tech-httpx
description: Reference guide for httpx — synchronous HTTP client for GBIF API calls
user-invocable: false
---

# httpx

> Purpose: Synchronous HTTP client for GBIF API calls
> Docs: https://www.python-httpx.org/
> Version researched: 0.28+

## Quick Start

```python
import httpx

with httpx.Client(base_url="https://api.gbif.org/v1", timeout=10.0) as client:
    response = client.get("/species/match", params={"name": "Puma concolor"})
    response.raise_for_status()
    data = response.json()
```

## Common Patterns

### Persistent client with base URL and timeout

```python
client = httpx.Client(
    base_url="https://api.gbif.org/v1",
    timeout=httpx.Timeout(connect=5.0, read=30.0, write=5.0, pool=5.0),
    headers={"User-Agent": "bio-explorer/1.0"},
)
```

Create the client once at module level and reuse it — this pools TCP connections across requests.

### Query parameters

```python
response = client.get("/occurrence/search", params={
    "taxonKey": 2435099,
    "limit": 300,
    "offset": 0,
    "hasCoordinate": "true",
})
```

Params are URL-encoded automatically; pass them as a dict, never format them into the URL string.

### Error handling

```python
try:
    response = client.get("/species/match", params={"name": query})
    response.raise_for_status()
    return response.json()
except httpx.HTTPStatusError as exc:
    # 4xx / 5xx from GBIF
    raise GBIFError(f"GBIF returned {exc.response.status_code}") from exc
except httpx.RequestError as exc:
    # Network-level failure: DNS, timeout, connection refused
    raise GBIFError("GBIF unreachable") from exc
```

### Paginating a large result set

```python
def fetch_all_occurrences(client: httpx.Client, taxon_key: int, limit: int = 300):
    offset = 0
    while True:
        r = client.get("/occurrence/search", params={
            "taxonKey": taxon_key,
            "limit": limit,
            "offset": offset,
            "hasCoordinate": "true",
        })
        r.raise_for_status()
        body = r.json()
        yield from body["results"]
        if body.get("endOfRecords", True):
            break
        offset += limit
```

## Gotchas & Pitfalls

- `httpx.get(url)` creates a new client per call — this is fine for one-off scripts but wasteful in a server context. Always use a shared `httpx.Client` instance for repeated calls.
- `raise_for_status()` raises `HTTPStatusError` only for 4xx/5xx. A 200 response with an error body will not raise; inspect `response.json()` yourself.
- `httpx.RequestError` is the base class for all transport-level errors (timeout, DNS failure, etc.). `httpx.TimeoutException` is a subclass of it.
- Default timeout is 5 seconds. GBIF paginated queries can be slow; raise `read` timeout to 30s+ for large occurrence fetches.
- `response.json()` raises `json.JSONDecodeError` if the body is not valid JSON (e.g., a plain text error response from GBIF). Guard with a try/except or check `response.headers["content-type"]`.

## Idiomatic Usage

Create the client once, close it with a context manager or explicitly at shutdown:

```python
# Good — module-level client, closed at app teardown
_client: httpx.Client | None = None

def get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(base_url="https://api.gbif.org/v1", timeout=20.0)
    return _client
```

Always check both `HTTPStatusError` and `RequestError` — never catch only one:

```python
# Good
except (httpx.HTTPStatusError, httpx.RequestError):
    ...

# Avoid — misses network-level failures
except httpx.HTTPStatusError:
    ...
```

Pass structured `params` dicts, never f-string query strings:

```python
# Good
client.get("/occurrence/search", params={"taxonKey": key, "limit": 300})

# Avoid
client.get(f"/occurrence/search?taxonKey={key}&limit=300")
```
