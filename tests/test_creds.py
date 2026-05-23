import aqdrop.creds as creds
import pytest


def test_resolve_token_prefers_explicit_token(monkeypatch):
    monkeypatch.setenv("NERSC_OIDC_TOKEN", "env-token")

    assert creds.resolve_token(token="arg-token") == "arg-token"


def test_resolve_token_uses_env_token(monkeypatch):
    monkeypatch.setenv("NERSC_OIDC_TOKEN", "env-token")

    assert creds.resolve_token() == "env-token"


def test_resolve_token_fetches_sfapi_token(monkeypatch):
    monkeypatch.delenv("NERSC_OIDC_TOKEN", raising=False)
    monkeypatch.setenv("AQDROP_CLIENT_ID", "client-123")
    monkeypatch.setenv("AQDROP_PRIVATE_KEY_PATH", "/tmp/key.pem")

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
        "token_url": None,
    }


def test_resolve_token_requires_complete_sfapi_config(monkeypatch):
    monkeypatch.delenv("NERSC_OIDC_TOKEN", raising=False)
    monkeypatch.setenv("AQDROP_CLIENT_ID", "client-123")
    monkeypatch.delenv("AQDROP_PRIVATE_KEY_PATH", raising=False)

    with pytest.raises(NameError, match="Both AQDROP_CLIENT_ID and AQDROP_PRIVATE_KEY_PATH"):
        creds.resolve_token()
