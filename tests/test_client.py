import httpx

from aqdrop.main import AqdropClient


class DummyResponse:
    def raise_for_status(self):
        return None


class DummyHttpxClient:
    def __init__(self, *args, **kwargs):
        self.calls = []

    def request(self, method, path, headers=None, **kwargs):
        self.calls.append(
            {
                "method": method,
                "path": path,
                "headers": headers or {},
                "kwargs": kwargs,
            }
        )
        return DummyResponse()


def test_client_resolves_token_from_sfapi_credentials(monkeypatch):
    dummy_client = DummyHttpxClient()

    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: dummy_client)
    monkeypatch.setattr(
        "aqdrop.main.creds.resolve_token",
        lambda token=None, client_id=None, private_key_path=None, token_url=None: "resolved-token",
    )

    client = AqdropClient(
        host="https://aqdrop.example",
        client_id="client-123",
        private_key_path="/tmp/key.pem",
    )
    client._request("GET", "/members/")

    assert dummy_client.calls[0]["headers"]["Authorization"] == "Bearer resolved-token"


def test_client_prefers_direct_token(monkeypatch):
    dummy_client = DummyHttpxClient()

    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: dummy_client)

    captured = {}

    def fake_resolve(token=None, client_id=None, private_key_path=None, token_url=None):
        captured["token"] = token
        captured["client_id"] = client_id
        captured["private_key_path"] = private_key_path
        captured["token_url"] = token_url
        return token

    monkeypatch.setattr("aqdrop.main.creds.resolve_token", fake_resolve)

    client = AqdropClient(
        host="https://aqdrop.example",
        token="direct-token",
        client_id="client-123",
        private_key_path="/tmp/key.pem",
        token_url="https://oidc.example/token",
    )
    client._request("GET", "/members/")

    assert captured == {
        "token": "direct-token",
        "client_id": "client-123",
        "private_key_path": "/tmp/key.pem",
        "token_url": "https://oidc.example/token",
    }
    assert dummy_client.calls[0]["headers"]["Authorization"] == "Bearer direct-token"
