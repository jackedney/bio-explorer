"""Shared test fixtures."""

import pytest
from flask.testing import FlaskClient

from bio_explorer.app import create_app


@pytest.fixture
def client() -> FlaskClient:
    """Create a Flask test client with TESTING enabled."""
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()
