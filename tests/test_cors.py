import os
import pytest
from fastapi.testclient import TestClient

from backend.app import DEFAULT_TRUSTED_ORIGINS, app, get_allowed_origins


@pytest.fixture
def client():
    return TestClient(app)


class TestCORSConfiguration:
    def test_default_trusted_origins_list(self):
        """Default trusted origins should include standard local frontend dev ports."""
        assert "http://localhost:3000" in DEFAULT_TRUSTED_ORIGINS
        assert "http://127.0.0.1:3000" in DEFAULT_TRUSTED_ORIGINS
        assert "http://localhost:8000" in DEFAULT_TRUSTED_ORIGINS
        assert "http://localhost:8080" in DEFAULT_TRUSTED_ORIGINS
        assert "*" not in DEFAULT_TRUSTED_ORIGINS

    def test_get_allowed_origins_env_override(self, monkeypatch):
        """WARDEN_ALLOWED_ORIGINS env var should override allowed origins."""
        monkeypatch.setenv(
            "WARDEN_ALLOWED_ORIGINS",
            "https://dashboard.warden-z.ibm.com, https://warden.internal:8443",
        )
        custom = get_allowed_origins()
        assert custom == [
            "https://dashboard.warden-z.ibm.com",
            "https://warden.internal:8443",
        ]

    def test_get_allowed_origins_default_fallback(self, monkeypatch):
        """Empty env var should fall back to DEFAULT_TRUSTED_ORIGINS."""
        monkeypatch.delenv("WARDEN_ALLOWED_ORIGINS", raising=False)
        assert get_allowed_origins() == DEFAULT_TRUSTED_ORIGINS

    def test_trusted_origin_simple_request(self, client):
        """Trusted origin should receive allow-origin and allow-credentials headers."""
        trusted_origin = "http://localhost:3000"
        response = client.get("/health", headers={"Origin": trusted_origin})

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == trusted_origin
        assert response.headers.get("access-control-allow-credentials") == "true"
        # Wildcard must never be used with credentials
        assert response.headers.get("access-control-allow-origin") != "*"

    def test_untrusted_origin_simple_request(self, client):
        """Untrusted origin should NOT receive access-control-allow-origin."""
        untrusted_origin = "https://malicious-attacker.evil.com"
        response = client.get("/health", headers={"Origin": untrusted_origin})

        assert response.status_code == 200
        assert "access-control-allow-origin" not in response.headers

    def test_preflight_options_trusted_origin(self, client):
        """OPTIONS preflight for trusted origin returns 200 and required CORS headers."""
        trusted_origin = "http://localhost:3000"
        headers = {
            "Origin": trusted_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type, authorization",
        }
        response = client.options("/actions/execute", headers=headers)

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == trusted_origin
        assert response.headers.get("access-control-allow-credentials") == "true"
        allow_methods = response.headers.get("access-control-allow-methods", "")
        assert "POST" in allow_methods

    def test_preflight_options_untrusted_origin(self, client):
        """OPTIONS preflight for untrusted origin does NOT grant CORS permissions."""
        untrusted_origin = "http://unauthorized-domain.com"
        headers = {
            "Origin": untrusted_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
        response = client.options("/actions/execute", headers=headers)

        # Preflight should not grant allow-origin for untrusted callers
        assert response.headers.get("access-control-allow-origin") != untrusted_origin

    def test_preflight_options_supported_methods(self, client):
        """All required API methods are allowed during preflight."""
        trusted_origin = "http://127.0.0.1:8000"
        headers = {
            "Origin": trusted_origin,
            "Access-Control-Request-Method": "OPTIONS",
        }
        response = client.options("/actions/execute", headers=headers)
        assert response.status_code == 200
        allow_methods = response.headers.get("access-control-allow-methods", "")
        for method in ["GET", "POST", "OPTIONS"]:
            assert method in allow_methods
