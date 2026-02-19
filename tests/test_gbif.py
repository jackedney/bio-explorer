"""Tests for the GBIF API client module."""

import httpx
from hypothesis import given, settings
from hypothesis import strategies as st

from bio_explorer.gbif import (
    MAX_OCCURRENCE_POINTS,
    _get_client,
    get_occurrences,
    sample_points,
    search_species,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_DUMMY_REQUEST = httpx.Request("GET", "https://api.gbif.org/v1/test")


def _make_response(status_code: int, *, json: dict) -> httpx.Response:
    """Build an httpx.Response with a request attached."""
    return httpx.Response(
        status_code,
        json=json,
        request=_DUMMY_REQUEST,
    )


def _mock_client(monkeypatch, handler):
    """Replace the module-level httpx client with a mock.

    ``handler`` receives ``(url, **kwargs)`` and must return an
    ``httpx.Response``.
    """
    from bio_explorer import gbif as _gbif_mod

    class _FakeClient:
        def get(self, url, **kwargs):
            return handler(url, **kwargs)

    monkeypatch.setattr(_gbif_mod, "_client", _FakeClient())


# ---------------------------------------------------------------------------
# search_species
# ---------------------------------------------------------------------------


def test_search_species_exact_match_returns_correct_shape(monkeypatch):
    """An exact match returns a list with the primary result."""

    def handler(url, **kwargs):
        return _make_response(
            200,
            json={
                "matchType": "EXACT",
                "usageKey": 2435099,
                "scientificName": "Puma concolor",
                "vernacularName": "Mountain Lion",
                "rank": "SPECIES",
                "alternatives": [],
            },
        )

    _mock_client(monkeypatch, handler)

    results = search_species("mountain lion")

    assert len(results) == 1
    result = results[0]
    assert result["key"] == 2435099
    assert result["scientificName"] == "Puma concolor"
    assert result["commonName"] == "Mountain Lion"
    assert result["rank"] == "SPECIES"


def test_search_species_no_match_returns_empty_list(monkeypatch):
    """When GBIF finds no match, an empty list is returned."""

    def handler(url, **kwargs):
        return _make_response(
            200,
            json={"matchType": "NONE"},
        )

    _mock_client(monkeypatch, handler)

    results = search_species("xyznotaspecies")

    assert results == []


def test_search_species_includes_alternatives(monkeypatch):
    """Alternatives from GBIF are included after the primary match."""

    def handler(url, **kwargs):
        return _make_response(
            200,
            json={
                "matchType": "FUZZY",
                "usageKey": 100,
                "scientificName": "Alpha beta",
                "rank": "SPECIES",
                "alternatives": [
                    {
                        "usageKey": 200,
                        "scientificName": "Gamma delta",
                        "vernacularName": "Common G",
                        "rank": "SPECIES",
                    },
                ],
            },
        )

    _mock_client(monkeypatch, handler)

    results = search_species("alpha")

    assert len(results) == 2
    assert results[0]["key"] == 100
    assert results[1]["key"] == 200
    assert results[1]["commonName"] == "Common G"


# ---------------------------------------------------------------------------
# get_occurrences — single page
# ---------------------------------------------------------------------------


def test_get_occurrences_single_page_returns_points(monkeypatch):
    """A single-page response returns all coordinate pairs."""

    def handler(url, **kwargs):
        return _make_response(
            200,
            json={
                "count": 2,
                "endOfRecords": True,
                "results": [
                    {"decimalLatitude": 51.5, "decimalLongitude": -0.1},
                    {"decimalLatitude": 48.8, "decimalLongitude": 2.3},
                ],
            },
        )

    _mock_client(monkeypatch, handler)

    result = get_occurrences(2435099)

    assert result["total"] == 2
    assert result["returned"] == 2
    assert result["points"] == [[51.5, -0.1], [48.8, 2.3]]


# ---------------------------------------------------------------------------
# get_occurrences — multi-page
# ---------------------------------------------------------------------------


def test_get_occurrences_multi_page_collects_all_points(monkeypatch):
    """Pagination collects points across multiple pages."""
    call_count = 0

    def handler(url, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_response(
                200,
                json={
                    "count": 4,
                    "endOfRecords": False,
                    "results": [
                        {"decimalLatitude": 1.0, "decimalLongitude": 2.0},
                        {"decimalLatitude": 3.0, "decimalLongitude": 4.0},
                    ],
                },
            )
        return _make_response(
            200,
            json={
                "count": 4,
                "endOfRecords": True,
                "results": [
                    {"decimalLatitude": 5.0, "decimalLongitude": 6.0},
                    {"decimalLatitude": 7.0, "decimalLongitude": 8.0},
                ],
            },
        )

    _mock_client(monkeypatch, handler)

    result = get_occurrences(12345)

    assert result["total"] == 4
    assert result["returned"] == 4
    assert len(result["points"]) == 4


# ---------------------------------------------------------------------------
# get_occurrences — sampling cap
# ---------------------------------------------------------------------------


def test_get_occurrences_samples_when_exceeding_cap(monkeypatch):
    """When points exceed MAX_OCCURRENCE_POINTS, result is sampled down."""
    big_results = [
        {"decimalLatitude": float(i), "decimalLongitude": float(i)}
        for i in range(12_000)
    ]

    def handler(url, **kwargs):
        return _make_response(
            200,
            json={
                "count": 12_000,
                "endOfRecords": True,
                "results": big_results,
            },
        )

    _mock_client(monkeypatch, handler)

    result = get_occurrences(99999)

    assert result["total"] == 12_000
    assert result["returned"] == MAX_OCCURRENCE_POINTS
    assert len(result["points"]) == MAX_OCCURRENCE_POINTS


# ---------------------------------------------------------------------------
# get_occurrences — null coordinate filtering
# ---------------------------------------------------------------------------


def test_get_occurrences_skips_null_coordinates(monkeypatch):
    """Records with null lat or lng are excluded."""

    def handler(url, **kwargs):
        return _make_response(
            200,
            json={
                "count": 3,
                "endOfRecords": True,
                "results": [
                    {"decimalLatitude": 10.0, "decimalLongitude": 20.0},
                    {"decimalLatitude": None, "decimalLongitude": 30.0},
                    {"decimalLatitude": 40.0, "decimalLongitude": None},
                ],
            },
        )

    _mock_client(monkeypatch, handler)

    result = get_occurrences(111)

    assert result["returned"] == 1
    assert result["points"] == [[10.0, 20.0]]


# ---------------------------------------------------------------------------
# sample_points — unit tests
# ---------------------------------------------------------------------------


def test_sample_points_returns_all_when_under_cap():
    """When points are within the cap, they are returned unchanged."""
    points = [[1.0, 2.0], [3.0, 4.0]]
    result = sample_points(points, cap=10)

    assert result is points


def test_sample_points_samples_down_when_over_cap():
    """When points exceed the cap, the result is exactly cap-sized."""
    points = [[float(i), float(i)] for i in range(100)]
    result = sample_points(points, cap=10)

    assert len(result) == 10


# ---------------------------------------------------------------------------
# sample_points — Hypothesis property tests
# ---------------------------------------------------------------------------


@given(
    st.lists(
        st.tuples(
            st.floats(min_value=-90, max_value=90),
            st.floats(min_value=-180, max_value=180),
        ),
        min_size=0,
        max_size=50_000,
    )
)
@settings(max_examples=50)
def test_sample_points_never_exceeds_cap(raw_points):
    """Sampled output is always at most cap points."""
    points = [[lat, lng] for lat, lng in raw_points]
    cap = 100
    sampled = sample_points(points, cap=cap)

    assert len(sampled) <= cap


@given(
    st.lists(
        st.tuples(
            st.floats(min_value=-90, max_value=90),
            st.floats(min_value=-180, max_value=180),
        ),
        min_size=0,
        max_size=1_000,
    )
)
@settings(max_examples=50)
def test_sample_points_preserves_valid_coordinates(raw_points):
    """All sampled points have valid latitude and longitude ranges."""
    points = [[lat, lng] for lat, lng in raw_points]
    sampled = sample_points(points, cap=100)

    for point in sampled:
        assert len(point) == 2
        assert -90 <= point[0] <= 90
        assert -180 <= point[1] <= 180


# ---------------------------------------------------------------------------
# _get_client returns a shared instance
# ---------------------------------------------------------------------------


def test_get_client_returns_httpx_client(monkeypatch):
    """_get_client creates and returns an httpx.Client."""
    from bio_explorer import gbif as _gbif_mod

    monkeypatch.setattr(_gbif_mod, "_client", None)
    client = _get_client()

    assert isinstance(client, httpx.Client)

    # Cleanup: reset to None so other tests are not affected.
    monkeypatch.setattr(_gbif_mod, "_client", None)
