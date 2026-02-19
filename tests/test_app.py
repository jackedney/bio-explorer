"""Route tests for the Flask application."""

import httpx
import pytest
from flask.testing import FlaskClient

from bio_explorer import gbif


def test_index_returns_200(client: FlaskClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200


def test_species_search_missing_query_returns_400(client: FlaskClient) -> None:
    resp = client.get("/api/species/search")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "q parameter required"


def test_species_search_with_query_returns_results(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_results = [
        {
            "key": 2435099,
            "scientificName": "Puma concolor",
            "commonName": "Mountain Lion",
            "rank": "SPECIES",
        },
    ]
    monkeypatch.setattr(gbif, "search_species", lambda _query: fake_results)

    resp = client.get("/api/species/search?q=mountain+lion")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "results" in data
    assert isinstance(data["results"], list)
    assert data["results"][0]["key"] == 2435099


def test_occurrences_missing_taxon_key_returns_400(client: FlaskClient) -> None:
    resp = client.get("/api/occurrences")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "taxon_key parameter required"


def test_occurrences_invalid_taxon_key_returns_400(client: FlaskClient) -> None:
    resp = client.get("/api/occurrences?taxon_key=abc")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "taxon_key must be an integer"


def test_occurrences_with_taxon_key_returns_data(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_result = {
        "points": [[40.0, -3.0], [41.0, -4.0]],
        "total": 2,
        "returned": 2,
    }
    monkeypatch.setattr(gbif, "get_occurrences", lambda _key: fake_result)

    resp = client.get("/api/occurrences?taxon_key=2435099")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "points" in data
    assert "total" in data
    assert "returned" in data
    assert len(data["points"]) == 2


def test_species_search_gbif_error_returns_502(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_http_error(_query: str) -> None:
        raise httpx.HTTPError("connection failed")

    monkeypatch.setattr(gbif, "search_species", raise_http_error)

    resp = client.get("/api/species/search?q=puma")
    assert resp.status_code == 502
    assert resp.get_json()["error"] == "GBIF service unavailable"


def test_occurrences_gbif_error_returns_502(
    client: FlaskClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_http_error(_key: int) -> None:
        raise httpx.HTTPError("connection failed")

    monkeypatch.setattr(gbif, "get_occurrences", raise_http_error)

    resp = client.get("/api/occurrences?taxon_key=2435099")
    assert resp.status_code == 502
    assert resp.get_json()["error"] == "GBIF service unavailable"
