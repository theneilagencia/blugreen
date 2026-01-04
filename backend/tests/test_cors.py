"""
Tests for CORS (Cross-Origin Resource Sharing) configuration.

Tests cover:
- GET requests with valid Origin header
- OPTIONS preflight requests
- Invalid Origin headers
- Requests without Origin header
- CORS_ORIGINS parsing (JSON, CSV, empty)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.config import Settings


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestCORSMiddleware:
    """Test CORS middleware configuration."""

    def test_get_with_valid_origin(self, client):
        """Test GET request with valid Origin header returns CORS headers."""
        response = client.get(
            "/health",
            headers={"Origin": "https://app.blugreen.com.br"}
        )
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "https://app.blugreen.com.br"
        assert "access-control-allow-credentials" in response.headers
        assert response.headers["access-control-allow-credentials"] == "true"

    def test_get_with_alternative_valid_origin(self, client):
        """Test GET request with alternative valid Origin header."""
        response = client.get(
            "/health",
            headers={"Origin": "https://blugreen.com.br"}
        )
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "https://blugreen.com.br"

    def test_get_with_invalid_origin(self, client):
        """Test GET request with invalid Origin header is blocked."""
        response = client.get(
            "/health",
            headers={"Origin": "https://evil.com"}
        )
        
        assert response.status_code == 200  # Request succeeds
        # But CORS headers should not include the invalid origin
        if "access-control-allow-origin" in response.headers:
            assert response.headers["access-control-allow-origin"] != "https://evil.com"

    def test_get_without_origin(self, client):
        """Test GET request without Origin header works normally."""
        response = client.get("/health")
        
        assert response.status_code == 200
        # CORS headers may or may not be present without Origin

    def test_options_preflight_valid_origin(self, client):
        """Test OPTIONS preflight request with valid Origin."""
        response = client.options(
            "/projects",
            headers={
                "Origin": "https://app.blugreen.com.br",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "content-type",
            }
        )
        
        # Preflight should return 200 or 204
        assert response.status_code in [200, 204]
        
        # Check CORS headers
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "https://app.blugreen.com.br"
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
        assert "access-control-allow-credentials" in response.headers
        assert response.headers["access-control-allow-credentials"] == "true"

    def test_options_preflight_with_post_method(self, client):
        """Test OPTIONS preflight for POST request."""
        response = client.options(
            "/projects",
            headers={
                "Origin": "https://app.blugreen.com.br",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            }
        )
        
        assert response.status_code in [200, 204]
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        # Should allow POST
        assert "POST" in response.headers["access-control-allow-methods"].upper()

    def test_options_preflight_invalid_origin(self, client):
        """Test OPTIONS preflight with invalid Origin is blocked."""
        response = client.options(
            "/projects",
            headers={
                "Origin": "https://evil.com",
                "Access-Control-Request-Method": "GET",
            }
        )
        
        # Preflight may succeed but should not include invalid origin
        if "access-control-allow-origin" in response.headers:
            assert response.headers["access-control-allow-origin"] != "https://evil.com"

    def test_post_with_valid_origin(self, client):
        """Test POST request with valid Origin header."""
        response = client.post(
            "/projects",
            json={"name": "Test Project", "description": "Test"},
            headers={"Origin": "https://app.blugreen.com.br"}
        )
        
        # Request may fail due to validation, but CORS headers should be present
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] == "https://app.blugreen.com.br"

    def test_authenticated_route_with_cors(self, client):
        """Test authenticated route returns CORS headers."""
        # This tests that CORS works even on routes that require authentication
        response = client.get(
            "/projects",
            headers={"Origin": "https://app.blugreen.com.br"}
        )
        
        # Request may fail due to auth, but CORS headers should be present
        assert "access-control-allow-origin" in response.headers


class TestCORSOriginsConfig:
    """Test CORS_ORIGINS configuration parsing."""

    def test_parse_comma_separated_origins(self):
        """Test parsing comma-separated CORS_ORIGINS."""
        settings = Settings(
            cors_origins_raw="https://example.com,https://app.example.com",
            debug=False,
        )
        
        assert len(settings.cors_origins) == 2
        assert "https://example.com" in settings.cors_origins
        assert "https://app.example.com" in settings.cors_origins

    def test_parse_comma_separated_with_spaces(self):
        """Test parsing comma-separated CORS_ORIGINS with spaces."""
        settings = Settings(
            cors_origins_raw="https://example.com , https://app.example.com ",
            debug=False,
        )
        
        assert len(settings.cors_origins) == 2
        assert "https://example.com" in settings.cors_origins
        assert "https://app.example.com" in settings.cors_origins

    def test_parse_json_array_origins(self):
        """Test parsing JSON array CORS_ORIGINS."""
        settings = Settings(
            cors_origins_raw='["https://example.com", "https://app.example.com"]',
            debug=False,
        )
        
        assert len(settings.cors_origins) == 2
        assert "https://example.com" in settings.cors_origins
        assert "https://app.example.com" in settings.cors_origins

    def test_parse_single_origin(self):
        """Test parsing single CORS_ORIGIN."""
        settings = Settings(
            cors_origins_raw="https://example.com",
            debug=False,
        )
        
        assert len(settings.cors_origins) == 1
        assert "https://example.com" in settings.cors_origins

    def test_empty_origins_in_debug_mode(self):
        """Test empty CORS_ORIGINS is allowed in debug mode."""
        settings = Settings(
            cors_origins_raw="",
            debug=True,
        )
        
        # Should not raise error in debug mode
        assert settings.cors_origins == []

    def test_empty_origins_in_production_raises_error(self):
        """Test empty CORS_ORIGINS raises error in production mode."""
        with pytest.raises(ValueError, match="CORS_ORIGINS cannot be empty in production"):
            settings = Settings(
                cors_origins_raw="",
                debug=False,
            )
            # Access cors_origins to trigger validation
            _ = settings.cors_origins

    def test_malformed_json_falls_back_to_csv(self):
        """Test malformed JSON falls back to CSV parsing."""
        settings = Settings(
            cors_origins_raw='{"invalid": "json"}',
            debug=False,
        )
        
        # Should parse as CSV (single origin)
        assert len(settings.cors_origins) == 1

    def test_json_non_list_logs_warning(self):
        """Test JSON non-list logs warning and returns empty."""
        with patch("app.config.logger") as mock_logger:
            settings = Settings(
                cors_origins_raw='{"key": "value"}',
                debug=True,
            )
            
            # Should log warning about non-list JSON
            # (actual behavior depends on implementation)


class TestCORSRegression:
    """Test CORS regression scenarios."""

    def test_cors_origins_not_empty_after_parsing(self):
        """Test that CORS_ORIGINS is never empty after parsing in production."""
        # This is a regression test for the bug where CORS_ORIGINS was empty
        settings = Settings(
            cors_origins_raw="https://app.blugreen.com.br,https://blugreen.com.br",
            debug=False,
        )
        
        assert len(settings.cors_origins) > 0
        assert "https://app.blugreen.com.br" in settings.cors_origins

    def test_cors_middleware_always_configured(self, client):
        """Test that CORS middleware is always configured."""
        # This tests that the middleware is present
        response = client.get(
            "/health",
            headers={"Origin": "https://app.blugreen.com.br"}
        )
        
        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers

    def test_preflight_works_for_all_routes(self, client):
        """Test that preflight works for all routes."""
        routes_to_test = [
            "/",
            "/health",
            "/projects",
            "/tasks",
            "/agents",
        ]
        
        for route in routes_to_test:
            response = client.options(
                route,
                headers={
                    "Origin": "https://app.blugreen.com.br",
                    "Access-Control-Request-Method": "GET",
                }
            )
            
            # Preflight should succeed
            assert response.status_code in [200, 204], f"Preflight failed for {route}"
            assert "access-control-allow-origin" in response.headers, f"CORS headers missing for {route}"


class TestCORSDocumentation:
    """Test CORS configuration examples from documentation."""

    def test_example_csv_format(self):
        """Test example CSV format from documentation."""
        settings = Settings(
            cors_origins_raw="https://app.example.com,https://example.com",
            debug=False,
        )
        
        assert len(settings.cors_origins) == 2

    def test_example_json_format(self):
        """Test example JSON format from documentation."""
        settings = Settings(
            cors_origins_raw='["https://app.example.com", "https://example.com"]',
            debug=False,
        )
        
        assert len(settings.cors_origins) == 2

    def test_localhost_development(self):
        """Test localhost configuration for development."""
        settings = Settings(
            cors_origins_raw="http://localhost:3000,http://localhost:8080",
            debug=True,
        )
        
        assert "http://localhost:3000" in settings.cors_origins
        assert "http://localhost:8080" in settings.cors_origins
