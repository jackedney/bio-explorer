---
name: optim-geospatial-data
description: Optimisation patterns for geospatial point data handling — relevant to GBIF occurrence fetching, sampling, and client-side heatmap rendering
user-invocable: false
---

# Geospatial Data Optimisation

> Relevance: The app fetches up to 100,000 GBIF occurrence records and renders them as a client-side heatmap. Payload size and rendering performance are the primary bottlenecks. SPEC constraint: 10,000-point cap for smooth Leaflet.heat rendering.

## Key Principles

1. **Send only what the client needs.** Coordinate pairs `[lat, lng]` are 16 bytes each. Strip all metadata (species name, date, dataset key) before sending to the browser.
2. **Sample early, not late.** Sample down to the target count in Python before serialising to JSON — never ship 50,000 points and discard them in JS.
3. **Preserve spatial distribution when sampling.** Simple random sampling maintains geographic density patterns better than first-N or page-based slicing.

## Recommended Patterns

### Efficient random sampling

```python
import random

def sample_points(
    points: list[list[float]],
    max_count: int = 10_000,
) -> list[list[float]]:
    """Return at most max_count points, preserving spatial distribution."""
    if len(points) <= max_count:
        return points
    return random.sample(points, max_count)
```

`random.sample` samples without replacement in O(n) time. For very large lists (>1M), consider `reservoir_sampling` instead to avoid building the full list in memory first.

### Stream-and-discard pagination

GBIF's occurrence API has a hard offset limit of 100,000 records and a max page size of 300. Paginate only as far as needed:

```python
def fetch_occurrence_coords(
    client: httpx.Client,
    taxon_key: int,
    target: int = 10_000,
) -> list[list[float]]:
    """Paginate GBIF until we have enough points or exhaust results."""
    points: list[list[float]] = []
    offset = 0
    page_size = 300

    while len(points) < target:
        r = client.get("/occurrence/search", params={
            "taxonKey": taxon_key,
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "limit": page_size,
            "offset": offset,
        })
        r.raise_for_status()
        body = r.json()
        for rec in body["results"]:
            lat = rec.get("decimalLatitude")
            lng = rec.get("decimalLongitude")
            if lat is not None and lng is not None:
                points.append([lat, lng])
        if body.get("endOfRecords", True):
            break
        offset += page_size

    return sample_points(points, target)
```

Stop paginating once `target` is exceeded — do not fetch all 100,000 if you only need 10,000.

### Compact JSON payload

```python
# Good — list of two-element arrays is the most compact JSON format
{"points": [[51.5, -0.1], [48.8, 2.3]], "total": 847231, "returned": 10000}

# Avoid — dict-per-point inflates payload ~3x
{"points": [{"lat": 51.5, "lng": -0.1}, ...]}
```

A 10,000-point payload as `[[lat, lng]]` arrays is approximately 250 KB. As dicts it would be ~700 KB.

### Float precision

GBIF coordinates are already at 6 decimal places (~0.1 m precision). Do not increase precision when re-serialising:

```python
# rounding is optional but keeps payload slightly smaller
points = [[round(r["decimalLatitude"], 5), round(r["decimalLongitude"], 5)]
          for r in results if r.get("decimalLatitude")]
```

## Data Structure Choices

| Use case | Structure | Why |
|---|---|---|
| Accumulating points during pagination | `list[list[float]]` | Append is O(1) amortised |
| Sampling | `list` (built-in `random.sample`) | No dependencies, O(n) |
| JSON serialisation | Nested lists | Smallest JSON representation |
| Intermediate coordinate filtering | List comprehension | Faster than explicit for-loop append |

Avoid `numpy` arrays for this use case — the overhead of importing and converting for a single paginated fetch outweighs any benefit.

## Measurement

```bash
# Measure API response time from Flask
poe run  # start the app
time curl "http://localhost:5000/api/occurrences?taxon_key=2435099"

# Profile Python code
python -m cProfile -s cumulative app.py
```

Key metrics to track:
- **Backend response time**: target <5s for a 10,000-point fetch (GBIF latency-bound)
- **JSON payload size**: target <300 KB for 10,000 points
- **Heatmap render time**: Leaflet.heat renders 10,000 points in ~100ms on modern hardware

## Common Pitfalls

- **Fetching all pages before returning**: GBIF's 100,000-record limit means pagination can require 333 requests at page size 300. Stop early once you have enough data.
- **Not filtering `hasCoordinate=true`**: GBIF records without coordinates will have `null` lat/lng values — filtering server-side avoids null-checking in Python.
- **Not filtering `hasGeospatialIssue=false`**: Records with coordinate issues (sea points on land, transposed lat/lng, default country centroids) degrade heatmap accuracy.
- **Serialising floats with full Python precision**: Python floats have 17 significant digits; 6 is sufficient for map rendering. `round(lat, 5)` saves space with no perceptible quality loss.
- **Accumulating across searches**: The frontend must call `heat.setLatLngs(newPoints)` (replace), not `addLatLng` in a loop (accumulate), on each new search.
