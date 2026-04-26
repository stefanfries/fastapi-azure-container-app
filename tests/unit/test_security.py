"""
Unit tests for app.core.security.require_api_key.

Tests cover three scenarios:
- Open mode:      API_KEY unset (None) → all requests pass
- Misconfigured:  API_KEY set to empty string → requests are rejected (401)
- Protected mode: API_KEY set → correct key passes, wrong/missing key → HTTP 401
"""

from unittest.mock import MagicMock, patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.core.security import require_api_key

# --------------------------------------------------------------------------- #
# Minimal FastAPI app used only by these tests
# --------------------------------------------------------------------------- #

_app = FastAPI()


@_app.get("/protected")
async def _protected_route(_=Depends(require_api_key)):
    return {"ok": True}


def _make_client() -> TestClient:
    return TestClient(_app, raise_server_exceptions=True)


def _mock_settings(api_key_value: str | None) -> MagicMock:
    """Return a settings mock with auth.api_key set to a SecretStr or None."""
    mock = MagicMock()
    mock.auth.api_key = None if api_key_value is None else SecretStr(api_key_value)
    return mock


# --------------------------------------------------------------------------- #
# Open mode — API_KEY absent or empty
# --------------------------------------------------------------------------- #


class TestOpenMode:
    def test_none_key_no_header_passes(self):
        """No API_KEY configured: request without header is allowed."""
        with patch("app.core.security.settings", _mock_settings(None)):
            response = _make_client().get("/protected")
        assert response.status_code == 200

    def test_none_key_with_any_header_passes(self):
        """No API_KEY configured: any X-API-Key value is ignored."""
        with patch("app.core.security.settings", _mock_settings(None)):
            response = _make_client().get("/protected", headers={"X-API-Key": "anything"})
        assert response.status_code == 200

    def test_empty_string_key_rejects_no_header(self):
        """API_KEY set to empty string: request without header returns 401."""
        with patch("app.core.security.settings", _mock_settings("")):
            response = _make_client().get("/protected")
        assert response.status_code == 401

    def test_empty_string_key_rejects_wrong_header(self):
        """API_KEY set to empty string: request with non-empty header returns 401."""
        with patch("app.core.security.settings", _mock_settings("")):
            response = _make_client().get("/protected", headers={"X-API-Key": "wrong"})
        assert response.status_code == 401


# --------------------------------------------------------------------------- #
# Protected mode — API_KEY set to a real value
# --------------------------------------------------------------------------- #


class TestProtectedMode:
    def test_correct_key_passes(self):
        """Correct X-API-Key header returns 200."""
        with patch("app.core.security.settings", _mock_settings("secret")):
            response = _make_client().get("/protected", headers={"X-API-Key": "secret"})
        assert response.status_code == 200

    def test_missing_header_returns_401(self):
        """No X-API-Key header returns 401 when a key is configured."""
        with patch("app.core.security.settings", _mock_settings("secret")):
            response = _make_client().get("/protected")
        assert response.status_code == 401

    def test_wrong_key_returns_401(self):
        """Wrong X-API-Key value returns 401."""
        with patch("app.core.security.settings", _mock_settings("secret")):
            response = _make_client().get("/protected", headers={"X-API-Key": "wrong"})
        assert response.status_code == 401

    def test_empty_header_value_returns_401(self):
        """Empty X-API-Key header value returns 401 when a key is configured."""
        with patch("app.core.security.settings", _mock_settings("secret")):
            response = _make_client().get("/protected", headers={"X-API-Key": ""})
        assert response.status_code == 401

    def test_401_detail_message(self):
        """401 response body contains the expected detail message."""
        with patch("app.core.security.settings", _mock_settings("secret")):
            response = _make_client().get("/protected", headers={"X-API-Key": "wrong"})
        assert response.json()["detail"] == "Invalid or missing API key"

    def test_401_www_authenticate_header(self):
        """401 response includes WWW-Authenticate: ApiKey header."""
        with patch("app.core.security.settings", _mock_settings("secret")):
            response = _make_client().get("/protected")
        assert response.headers.get("WWW-Authenticate") == "ApiKey"

    def test_key_is_case_sensitive(self):
        """API key comparison is case-sensitive."""
        with patch("app.core.security.settings", _mock_settings("Secret")):
            response = _make_client().get("/protected", headers={"X-API-Key": "secret"})
        assert response.status_code == 401
