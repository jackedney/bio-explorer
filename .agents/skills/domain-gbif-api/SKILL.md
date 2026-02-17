---
name: domain-gbif-api
description: Domain knowledge — GBIF API concepts for correct implementation of species search and occurrence fetching
user-invocable: false
---

# GBIF API

> Relevance: The entire data pipeline depends on correct use of GBIF's Species and Occurrence APIs. Misunderstanding the data model, offset limits, and coordinate quality flags leads to incorrect or empty results.

## Core Concepts

### Taxon keys

Every species (and higher taxon) in GBIF has a numeric **taxon key** — its identifier in the GBIF backbone taxonomy. Occurrence records reference this key, not species names. The species search workflow is always two steps:

1. Resolve a name string → taxon key (via `/species/match` or `/species/search`)
2. Fetch occurrences → by taxon key (via `/occurrence/search?taxonKey=...`)

```
/species/match?name=Puma%20concolor  →  { "usageKey": 2435099, ... }
/occurrence/search?taxonKey=2435099  →  { "results": [...], "count": 847231 }
```

### Species match vs species search

- `/v1/species/match?name=...` — fuzzy-matches a single name against the backbone. Returns one best match with a confidence score. Fast, suited for autocomplete/search.
- `/v1/species/search?q=...` — full-text search across names. Returns a paginated list of candidates. Better for browsing.

For this app's search-by-name use case, `/species/match` with the user's query is the primary endpoint. Follow up with `/species/search` if match confidence is low.

### Occurrence record structure

Each occurrence record from `/v1/occurrence/search` includes (among many fields):

| Field | Type | Notes |
|---|---|---|
| `decimalLatitude` | float or null | May be null if not georeferenced |
| `decimalLongitude` | float or null | May be null if not georeferenced |
| `taxonKey` | int | Matched backbone taxon |
| `hasCoordinate` | bool | True if lat/lng are present |
| `hasGeospatialIssue` | bool | True if GBIF flagged a coordinate problem |

The app only needs `decimalLatitude` and `decimalLongitude`. All other fields are noise.

### Pagination constraints

| Constraint | Value |
|---|---|
| Max `limit` per request | 300 |
| Hard offset ceiling | 100,000 |
| Max retrievable records via search | 100,000 |

To get more than 100,000 records, a GBIF download must be requested (asynchronous, email delivery — not suitable for this app). For a demo capped at 10,000 points, pagination stays well within the 100,000 limit.

### `endOfRecords` flag

The response body includes `"endOfRecords": true` when there are no more pages. Always check this — do not rely solely on whether `results` is empty, because the API may return an empty final page with `endOfRecords: false` in edge cases.

## Mental Models

**GBIF as a search engine, not a database.** The occurrence search API is optimised for filtering and exploring, not bulk export. It behaves like a web search: fast for small result sets, limited for full dumps. For the 10K-point use case, treat it as a paginated search endpoint, not a data warehouse.

**Taxon keys are stable, names are not.** Species names change due to taxonomic revisions. Taxon keys in the GBIF backbone are stable identifiers. Always work with keys once resolved; do not re-resolve names on each request.

**Coordinate quality is heterogeneous.** GBIF aggregates records from thousands of providers. A significant fraction have coordinate issues: country-level centroids, sea points for terrestrial species, transposed lat/lng (especially from older records). The `hasGeospatialIssue` flag catches the most common problems.

## Edge Cases and Gotchas

- **`decimalLatitude` can be null** even when `hasCoordinate=false` is not filtered — always guard with `if lat is not None and lng is not None`.
- **Species with very few records** may return `endOfRecords: true` on the first page with fewer results than `limit`. This is normal.
- **Subspecies and synonyms** have their own taxon keys. `/species/match` returns the accepted taxon by default. Occurrences are indexed under the accepted name's key.
- **GBIF rate limiting**: no published hard rate limit, but aggressive pagination (no delays, 300 records/request) can trigger 429 responses. For a demo, this is unlikely at 10K-point cap.
- **The `count` field in occurrence search** is the total matching records, not the number returned. Use it to report `total` in the API response; do not use it to control pagination.
- **UNEP-WCMC tile URLs use `{z}/{y}/{x}` not `{z}/{x}/{y}`** — this is a tile server convention difference, not a GBIF issue, but it affects the contextual layer integration.

## Validation Rules

A correctly implemented GBIF occurrence fetch satisfies:

1. All returned points have non-null latitude and longitude values
2. No returned points originated from records with `hasGeospatialIssue=true`
3. Returned count is at most `MAX_OCCURRENCE_POINTS` (10,000)
4. The `total` field reflects the full GBIF count, not the sampled count
5. `returned` equals `len(points)` in the response

Invariant to test:
```python
assert all(len(p) == 2 for p in response["points"])
assert all(-90 <= p[0] <= 90 for p in response["points"])   # valid latitude
assert all(-180 <= p[1] <= 180 for p in response["points"]) # valid longitude
assert response["returned"] == len(response["points"])
assert response["returned"] <= 10_000
```
