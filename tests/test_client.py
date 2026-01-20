#!/usr/bin/env python3
"""Tests for OuraClient API wrapper."""

import pytest
from pathlib import Path
import responses  # Use responses library for HTTP mocking

# Add scripts directory to path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from oura_api import OuraClient


class TestOuraClient:
    """Test OuraClient initialization and API methods."""

    def test_client_init_with_token(self):
        """Test client initialization with explicit token."""
        client = OuraClient(token="test_token_123")
        assert client.token == "test_token_123"
        assert "Bearer test_token_123" in client.headers["Authorization"]

    def test_client_init_from_env(self, monkeypatch):
        """Test client initialization from OURA_API_TOKEN env var."""
        monkeypatch.setenv("OURA_API_TOKEN", "env_token_456")
        client = OuraClient()
        assert client.token == "env_token_456"

    def test_client_init_missing_token(self):
        """Test that missing token raises ValueError."""
        import os
        # Backup and clear env var
        original = os.environ.get("OURA_API_TOKEN")
        os.environ.pop("OURA_API_TOKEN", None)
        try:
            with pytest.raises(ValueError, match="OURA_API_TOKEN not set"):
                OuraClient()
        finally:
            if original:
                os.environ["OURA_API_TOKEN"] = original

    @responses.activate
    def test_request_url_construction(self):
        """Test that _request constructs URL correctly."""
        responses.get(
            "https://api.ouraring.com/v2/usercollection/sleep",
            json={"data": [{"day": "2026-01-15", "score": 80}]}
        )

        client = OuraClient(token="test")
        result = client._request("sleep", "2026-01-01", "2026-01-15")

        assert len(result) == 1
        assert result[0]["day"] == "2026-01-15"
        assert "start_date=2026-01-01" in responses.calls[0].request.url
        assert "end_date=2026-01-15" in responses.calls[0].request.url

    @responses.activate
    def test_get_sleep_no_dates(self):
        """Test get_sleep returns all data when no dates specified."""
        responses.get(
            "https://api.ouraring.com/v2/usercollection/sleep",
            json={"data": [{"day": "2026-01-10"}, {"day": "2026-01-11"}]}
        )

        client = OuraClient(token="test")
        result = client.get_sleep()

        assert len(result) == 2
        assert "start_date" not in responses.calls[0].request.url

    @responses.activate
    def test_get_readiness(self):
        """Test get_readiness method."""
        responses.get(
            "https://api.ouraring.com/v2/usercollection/daily_readiness",
            json={"data": [{"day": "2026-01-15", "score": 75}]}
        )

        client = OuraClient(token="test")
        result = client.get_readiness("2026-01-01", "2026-01-15")

        assert len(result) == 1
        assert result[0]["score"] == 75

    @responses.activate
    def test_get_activity(self):
        """Test get_activity method."""
        responses.get(
            "https://api.ouraring.com/v2/usercollection/daily_activity",
            json={"data": [{"day": "2026-01-15", "score": 65}]}
        )

        client = OuraClient(token="test")
        result = client.get_activity("2026-01-01", "2026-01-15")

        assert len(result) == 1
        assert result[0]["score"] == 65

    @responses.activate
    def test_error_handling(self):
        """Test that HTTP errors are raised."""
        responses.get(
            "https://api.ouraring.com/v2/usercollection/sleep",
            status=401,
            json={"error": "Unauthorized"}
        )

        client = OuraClient(token="test")
        with pytest.raises(Exception):
            client.get_sleep("2026-01-01", "2026-01-15")
