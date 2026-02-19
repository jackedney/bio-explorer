"""GBIF API client for species search and occurrence fetching."""

import random

import httpx

MAX_OCCURRENCE_POINTS = 10_000
_PAGE_SIZE = 300

_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    """Return a shared httpx client, creating it on first use."""
    global _client  # noqa: PLW0603
    if _client is None:
        _client = httpx.Client(
            base_url="https://api.gbif.org/v1",
            timeout=20.0,
        )
    return _client


def sample_points(
    points: list[list[float]],
    cap: int = MAX_OCCURRENCE_POINTS,
) -> list[list[float]]:
    """Return at most *cap* points, preserving spatial distribution.

    Args:
        points: List of [latitude, longitude] pairs.
        cap: Maximum number of points to return.

    Returns:
        The original list if its length is within *cap*, otherwise a
        random sample of *cap* points.
    """
    if len(points) <= cap:
        return points
    return random.sample(points, cap)  # nosec B311


def search_species(query: str) -> list[dict]:
    """Resolve a species name to GBIF taxon matches.

    Args:
        query: Common or scientific species name.

    Returns:
        List of dicts, each with keys ``key``, ``scientificName``,
        ``commonName``, and ``rank``.  Returns an empty list when GBIF
        finds no match.
    """
    client = _get_client()
    response = client.get(
        "/species/match",
        params={"name": query, "verbose": True},
    )
    response.raise_for_status()
    data = response.json()

    match_type = data.get("matchType", "NONE")
    if match_type == "NONE":
        return []

    alternatives = data.get("alternatives", [])
    primary = {
        "key": data["usageKey"],
        "scientificName": data.get("scientificName", ""),
        "commonName": data.get("vernacularName", ""),
        "rank": data.get("rank", ""),
    }
    results = [primary]

    for alt in alternatives:
        results.append(
            {
                "key": alt["usageKey"],
                "scientificName": alt.get("scientificName", ""),
                "commonName": alt.get("vernacularName", ""),
                "rank": alt.get("rank", ""),
            }
        )

    return results


def get_occurrences(taxon_key: int) -> dict:
    """Fetch occurrence coordinates for a taxon from GBIF.

    Paginates through the GBIF Occurrence Search API, collecting
    ``[latitude, longitude]`` pairs.  If the total exceeds
    ``MAX_OCCURRENCE_POINTS``, the result is randomly sampled down to
    preserve spatial distribution while keeping the client-side heatmap
    performant.

    Args:
        taxon_key: GBIF numeric taxon key.

    Returns:
        Dict with ``points`` (list of ``[lat, lng]`` pairs), ``total``
        (full GBIF count), and ``returned`` (number of points in the
        response).
    """
    client = _get_client()
    points: list[list[float]] = []
    offset = 0
    total = 0

    while True:
        response = client.get(
            "/occurrence/search",
            params={
                "taxonKey": taxon_key,
                "hasCoordinate": "true",
                "hasGeospatialIssue": "false",
                "limit": _PAGE_SIZE,
                "offset": offset,
            },
        )
        response.raise_for_status()
        body = response.json()
        total = body.get("count", 0)

        for rec in body.get("results", []):
            lat = rec.get("decimalLatitude")
            lng = rec.get("decimalLongitude")
            if lat is not None and lng is not None:
                points.append([lat, lng])

        if body.get("endOfRecords", True):
            break
        offset += _PAGE_SIZE

    sampled = sample_points(points)
    return {
        "points": sampled,
        "total": total,
        "returned": len(sampled),
    }
