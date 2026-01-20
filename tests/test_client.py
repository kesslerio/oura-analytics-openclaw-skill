#!/usr/bin/env python3
"""Tests for OuraClient API wrapper."""

import pytest
from pathlib import Path

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

    def test_request_url_construction(self, requests_mock):
        """Test that _request constructs URL correctly."""
        requests_mock.get(
            "https://api.ouraring.com/v2/usercollection/sleep",
            json={"data": [{"day": "2026-01-15", "score": 80}]}
        )

        client = OuraClient(token="test")
        result = client._request("sleep", "2026-01-01", "2026-01-15")

        assert len(result) == 1
        assert result[0]["day"] == "2026-01-15"
        assert requests_mock.last_request.qs["start_date"] == ["2026-01-01"]
        assert requests_mock.last_request.qs["end_date"] == ["2026-01-15"]

    def test_get_sleep_no_dates(self, requests_mock):
        """Test get_sleep returns all data when no dates specified."""
        requests_mock.get(
            "https://api.ouraring.com/v2/usercollection/sleep",
            json={"data": [{"day": "2026-01-10"}, {"day": "2026-01-11"}]}
        )

        client = OuraClient(token="test")
        result = client.get_sleep()

        assert len(result) == 2
        assert "start_date" not in requests_mock.last_request.qs
        assert "end_date" not in requests_mock.last_request.qs

    def test_get_readiness(self, requests_mock):
        """Test get_readiness method."""
        requests_mock.get(
            "https://api.ouraring.com/v2/usercollection/daily_readiness",
            json={"data": [{"day": "2026-01-15", "score": 75}]}
        )

        client = OuraClient(token="test")
        result = client.get_readiness("2026-01-01", "2026-01-15")

        assert len(result) == 1
        assert result[0]["score"] == 75

    def test_get_activity(self, requests_mock):
        """Test get_activity method."""
        requests_mock.get(
            "https://api.ouraring.com/v2/usercollection/daily_activity",
            json={"data": [{"day": "2026-01-15", "score": 65}]}
        )

        client = OuraClient(token="test")
        result = client.get_activity("2026-01-01", "2026-01-15")

        assert len(result) == 1
        assert result[0]["score"] == 65

    def test_error_handling(self, requests_mock):
        """Test that HTTP errors are raised."""
        requests_mock.get(
            "https://api.ouraring.com/v2/usercollection/sleep",
            status_code=401,
            json={"error": "Unauthorized"}
        )

        client = OuraClient(token="test")
        with pytest.raises(Exception):
            client.get_sleep("2026-01-01", "2026-01-15")
