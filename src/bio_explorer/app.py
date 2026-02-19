"""Flask app factory, route registration, and error handlers."""

import httpx
from flask import Flask, render_template, request

from bio_explorer import gbif


def create_app() -> Flask:
    """Create and configure the Flask application.

    Returns:
        A configured Flask instance with API routes registered.
    """
    app = Flask(__name__)

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/api/species/search")
    def species_search() -> tuple[dict, int] | dict:
        query = request.args.get("q", "")
        if not query:
            return {"error": "q parameter required"}, 400
        try:
            results = gbif.search_species(query)
        except httpx.HTTPError:
            return {"error": "GBIF service unavailable"}, 502
        return {"results": results}

    @app.get("/api/occurrences")
    def occurrences() -> tuple[dict, int] | dict:
        taxon_key_raw = request.args.get("taxon_key", "")
        if not taxon_key_raw:
            return {"error": "taxon_key parameter required"}, 400
        try:
            taxon_key = int(taxon_key_raw)
        except ValueError:
            return {"error": "taxon_key must be an integer"}, 400
        try:
            result = gbif.get_occurrences(taxon_key)
        except httpx.HTTPError:
            return {"error": "GBIF service unavailable"}, 502
        return result

    return app
