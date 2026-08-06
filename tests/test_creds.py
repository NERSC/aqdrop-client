import base64
import json
import stat
import time

import aqdrop.creds as creds
import pytest


def _jwt(expiration, marker="token"):
    def encode(value):
        data = json.dumps(value, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    return f"{encode({'alg': 'RS256'})}.{encode({'exp': expiration, 'marker': marker})}.signature"


def test_resolve_token_prefers_explicit_token(monkeypatch):
    monkeypatch.setenv("SFAPI_TOKEN", "env-token")

    assert creds.resolve_token(token="arg-token") == "arg-token"


def test_resolve_token_uses_env_token(monkeypatch):
    monkeypatch.setenv("SFAPI_TOKEN", "env-token")

    assert creds.resolve_token() == "env-token"


def test_resolve_token_fetches_sfapi_token(monkeypatch):
    monkeypatch.delenv("SFAPI_TOKEN", raising=False)
    monkeypatch.setenv("SFAPI_CLIENT_ID", "client-123")
    monkeypatch.setenv("SFAPI_PRIVATE_KEY_PATH", "/tmp/key.pem")

    seen = {}

    def fake_fetch(client_id, private_key_path, token_url=None):
        seen["client_id"] = client_id
        seen["private_key_path"] = private_key_path
        seen["token_url"] = token_url
        return "fetched-token"

    monkeypatch.setattr(creds, "fetch_sfapi_token", fake_fetch)

    assert creds.resolve_token() == "fetched-token"
    assert seen == {
        "client_id": "client-123",
        "private_key_path": "/tmp/key.pem",
        "token_url": creds.DEFAULT_SFAPI_TOKEN_URL,
    }


def test_private_key_flow_reuses_unexpired_cached_token(tmp_path, monkeypatch):
    cache_directory = tmp_path / "cache"
    monkeypatch.setattr(creds, "_token_cache_directory", lambda: cache_directory)
    token = _jwt(time.time() + 600)
    fetches = []

    def fake_fetch(client_id, private_key_path, token_url=None):
        fetches.append((client_id, private_key_path, token_url))
        return token

    monkeypatch.setattr(creds, "fetch_sfapi_token", fake_fetch)

    assert creds.get_or_fetch_sfapi_token("client-123", "/tmp/key.pem") == token
    assert creds.get_or_fetch_sfapi_token("client-123", "/tmp/key.pem") == token
    assert len(fetches) == 1

    cache_files = list(cache_directory.glob("sfapi-token-*.json"))
    assert len(cache_files) == 1
    assert stat.S_IMODE(cache_directory.stat().st_mode) == 0o700
    assert stat.S_IMODE(cache_files[0].stat().st_mode) == 0o600


def test_private_key_flow_replaces_expired_cached_token(tmp_path, monkeypatch):
    cache_directory = tmp_path / "cache"
    monkeypatch.setattr(creds, "_token_cache_directory", lambda: cache_directory)
    expired_token = _jwt(time.time() - 60, "expired")
    fresh_token = _jwt(time.time() + 600, "fresh")
    cache_directory.mkdir(mode=0o700)
    cache_path = creds._token_cache_path("client-123", creds.DEFAULT_SFAPI_TOKEN_URL)
    cache_path.write_text(
        json.dumps({"access_token": expired_token}),
        encoding="utf-8",
    )
    cache_path.chmod(0o600)
    monkeypatch.setattr(creds, "fetch_sfapi_token", lambda *args, **kwargs: fresh_token)

    assert creds.get_or_fetch_sfapi_token("client-123", "/tmp/key.pem") == fresh_token


def test_refresh_sfapi_token_invalidates_cache(tmp_path, monkeypatch):
    cache_directory = tmp_path / "cache"
    monkeypatch.setattr(creds, "_token_cache_directory", lambda: cache_directory)
    cached_token = _jwt(time.time() + 600, "cached")
    refreshed_token = _jwt(time.time() + 600, "refreshed")
    creds._write_cached_sfapi_token(
        "client-123",
        creds.DEFAULT_SFAPI_TOKEN_URL,
        cached_token,
    )
    monkeypatch.setattr(creds, "fetch_sfapi_token", lambda *args, **kwargs: refreshed_token)

    assert creds.refresh_sfapi_token("client-123", "/tmp/key.pem") == refreshed_token
    assert (
        creds._read_cached_sfapi_token("client-123", creds.DEFAULT_SFAPI_TOKEN_URL)
        == refreshed_token
    )


def test_resolve_token_requires_complete_sfapi_config(monkeypatch):
    monkeypatch.delenv("SFAPI_TOKEN", raising=False)
    monkeypatch.setenv("SFAPI_CLIENT_ID", "client-123")
    monkeypatch.delenv("SFAPI_PRIVATE_KEY_PATH", raising=False)

    with pytest.raises(NameError, match="Both SFAPI_CLIENT_ID and SFAPI_PRIVATE_KEY_PATH"):
        creds.resolve_token()


def test_username_is_not_client_configuration():
    assert not hasattr(creds, "get_username")


def test_legacy_nersc_oidc_token_is_not_client_configuration(monkeypatch):
    monkeypatch.delenv("SFAPI_TOKEN", raising=False)
    monkeypatch.delenv("SFAPI_CLIENT_ID", raising=False)
    monkeypatch.delenv("SFAPI_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.setenv("NERSC_OIDC_TOKEN", "legacy-token")

    with pytest.raises(NameError, match="Set SFAPI_TOKEN directly"):
        creds.resolve_token()


def test_legacy_aqdrop_sfapi_environment_is_not_client_configuration(monkeypatch):
    monkeypatch.delenv("SFAPI_TOKEN", raising=False)
    monkeypatch.delenv("SFAPI_CLIENT_ID", raising=False)
    monkeypatch.delenv("SFAPI_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.setenv("AQDROP_CLIENT_ID", "legacy-client")
    monkeypatch.setenv("AQDROP_PRIVATE_KEY_PATH", "/tmp/legacy-key.pem")

    with pytest.raises(NameError, match="provide SFAPI_CLIENT_ID and SFAPI_PRIVATE_KEY_PATH"):
        creds.resolve_token()
