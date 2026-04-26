"""Tests for the GET /api/v1/ping endpoint."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Return a synchronous TestClient pointed at the FastAPI app.

    The lifespan is disabled so we don't need a real database or
    background services just to exercise the ping endpoint.
    """
    # Import inside the fixture so the module-level import doesn't trigger
    # heavy application startup before the fixture has a chance to patch.
    from agentorg.main import app

    # ``TestClient`` with ``raise_server_exceptions=True`` (the default)
    # will re-raise any unhandled exception from the server side, making
    # test failures easy to diagnose.
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


class TestPingEndpoint:
    """Behavioural tests for GET /api/v1/ping."""

    def test_status_code_is_200(self, client: TestClient) -> None:
        """The endpoint must respond with HTTP 200 OK."""
        response = client.get("/api/v1/ping")
        assert response.status_code == 200

    def test_response_body_contains_pong_true(self, client: TestClient) -> None:
        """The JSON body must be exactly {\"pong\": true}."""
        response = client.get("/api/v1/ping")
        assert response.json() == {"pong": True}

    def test_content_type_is_json(self, client: TestClient) -> None:
        """The response must carry a JSON content-type header."""
        response = client.get("/api/v1/ping")
        assert "application/json" in response.headers["content-type"]

    def test_pong_value_is_boolean_true(self, client: TestClient) -> None:
        """Confirm the value is a proper boolean True, not just a truthy string."""
        response = client.get("/api/v1/ping")
        pong = response.json()["pong"]
        assert pong is True
        assert isinstance(pong, bool)
