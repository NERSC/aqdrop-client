import httpx
import inspect
import pytest

from aqdrop import defs
from aqdrop.main import AqdropClient


class DummyResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.is_closed = False

    def close(self):
        self.is_closed = True

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://aqdrop.example/test")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=request,
                response=response,
            )
        return None

    def json(self):
        return self._payload


class DummyHttpxClient:
    def __init__(self, *args, responses=None, **kwargs):
        self.calls = []
        self.responses = list(responses or [])

    def request(self, method, path, headers=None, **kwargs):
        self.calls.append(
            {
                "method": method,
                "path": path,
                "headers": headers or {},
                "kwargs": kwargs,
            }
        )
        if self.responses:
            return self.responses.pop(0)
        return DummyResponse({})


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
    client._request("GET", "/queues/")

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
    client._request("GET", "/queues/")

    assert captured == {
        "token": "direct-token",
        "client_id": "client-123",
        "private_key_path": "/tmp/key.pem",
        "token_url": "https://oidc.example/token",
    }
    assert dummy_client.calls[0]["headers"]["Authorization"] == "Bearer direct-token"


def test_private_key_client_refreshes_once_after_unauthorized(monkeypatch):
    unauthorized = DummyResponse(status_code=401)
    success = DummyResponse({"ok": True})
    dummy_client = DummyHttpxClient(responses=[unauthorized, success])
    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: dummy_client)
    monkeypatch.setattr("aqdrop.main.creds.resolve_token", lambda **kwargs: "cached-token")

    refreshes = []

    def fake_refresh(client_id, private_key_path, token_url=None):
        refreshes.append((client_id, private_key_path, token_url))
        return "refreshed-token"

    monkeypatch.setattr("aqdrop.main.creds.refresh_sfapi_token", fake_refresh)

    client = AqdropClient(
        host="https://aqdrop.example",
        client_id="client-123",
        private_key_path="/tmp/key.pem",
        token_url="https://oidc.example/token",
    )
    response = client._request("GET", "/queues/")

    assert response.json() == {"ok": True}
    assert unauthorized.is_closed
    assert refreshes == [("client-123", "/tmp/key.pem", "https://oidc.example/token")]
    assert [call["headers"]["Authorization"] for call in dummy_client.calls] == [
        "Bearer cached-token",
        "Bearer refreshed-token",
    ]


def test_direct_token_client_does_not_refresh_after_unauthorized(monkeypatch):
    dummy_client = DummyHttpxClient(responses=[DummyResponse(status_code=401)])
    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: dummy_client)

    refreshes = []
    monkeypatch.setattr(
        "aqdrop.main.creds.refresh_sfapi_token",
        lambda *args, **kwargs: refreshes.append((args, kwargs)),
    )

    client = AqdropClient(host="https://aqdrop.example", token="direct-token")
    with pytest.raises(httpx.HTTPStatusError):
        client._request("GET", "/queues/")

    assert len(dummy_client.calls) == 1
    assert refreshes == []


def test_private_key_client_retries_unauthorized_only_once(monkeypatch):
    dummy_client = DummyHttpxClient(
        responses=[DummyResponse(status_code=401), DummyResponse(status_code=401)]
    )
    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: dummy_client)
    monkeypatch.setattr("aqdrop.main.creds.resolve_token", lambda **kwargs: "cached-token")

    refreshes = []

    def fake_refresh(*args):
        refreshes.append(args)
        return "refreshed-token"

    monkeypatch.setattr("aqdrop.main.creds.refresh_sfapi_token", fake_refresh)

    client = AqdropClient(
        host="https://aqdrop.example",
        client_id="client-123",
        private_key_path="/tmp/key.pem",
    )
    with pytest.raises(httpx.HTTPStatusError):
        client._request("GET", "/queues/")

    assert len(dummy_client.calls) == 2
    assert len(refreshes) == 1


def _client_with_dummy_transport(monkeypatch):
    dummy_client = DummyHttpxClient()
    monkeypatch.setattr(httpx, "Client", lambda *args, **kwargs: dummy_client)
    return AqdropClient(host="https://aqdrop.example", token="direct-token"), dummy_client


def test_add_queue_matches_clean_server_schema(monkeypatch):
    client, dummy_client = _client_with_dummy_transport(monkeypatch)

    client.add_queue("simulator", 3, defs.QueueType.SIMU, 8, description="Test queue")

    assert dummy_client.calls[0] == {
        "method": "POST",
        "path": "/queue/",
        "headers": {"Authorization": "Bearer direct-token"},
        "kwargs": {
            "json": {
                "name": "simulator",
                "limit_per_member": 3,
                "description": "Test queue",
                "type": defs.QueueType.SIMU,
                "max_qubits": 8,
            }
        },
    }


def test_update_queue_supports_current_server_fields(monkeypatch):
    client, dummy_client = _client_with_dummy_transport(monkeypatch)

    client.update_queue(
        "simulator",
        new_limit=4,
        new_state=defs.QueueState.CLOSED,
        new_max_qubits=12,
        new_type=defs.QueueType.QPU,
    )

    assert dummy_client.calls[0]["kwargs"]["json"] == {
        "limit_per_member": 4,
        "state": "closed",
        "max_qubits": 12,
        "type": "qpu",
    }


def test_query_jobs_uses_username_filter_without_legacy_owner_id(monkeypatch):
    client, dummy_client = _client_with_dummy_transport(monkeypatch)

    client.query_jobs(owner_name="other-user", max_jobs=2)

    assert "owner_id" not in inspect.signature(client.query_jobs).parameters
    assert dummy_client.calls[0]["kwargs"]["params"] == {
        "owner_name": "other-user",
        "max_jobs": 2,
    }


def test_member_management_methods_are_removed(monkeypatch):
    client, _ = _client_with_dummy_transport(monkeypatch)

    for method_name in (
        "create_member",
        "get_member_list",
        "get_member",
        "update_member",
        "delete_member",
        "update_member_perms",
        "list_members",
    ):
        assert not hasattr(client, method_name)
