import aqdrop.creds as creds
import pytest


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
        "token_url": None,
    }


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
