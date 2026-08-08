from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import time

DEFAULT_SFAPI_TOKEN_URL = "https://oidc.nersc.gov/c2id/token"
TOKEN_CACHE_EXPIRY_SKEW_SECONDS = 30


def get_token():
    token = os.getenv("SFAPI_TOKEN")
    if token is None:
        raise NameError("Environment variable SFAPI_TOKEN must be set!")
    return token


def get_client_id():
    client_id = os.getenv("SFAPI_CLIENT_ID")
    if client_id is None:
        raise NameError("Environment variable SFAPI_CLIENT_ID must be set!")
    return client_id


def get_private_key_path():
    private_key_path = os.getenv("SFAPI_PRIVATE_KEY_PATH")
    if private_key_path is None:
        raise NameError("Environment variable SFAPI_PRIVATE_KEY_PATH must be set!")
    return private_key_path


def get_token_url():
    return os.getenv("AQDROP_SFAPI_TOKEN_URL", DEFAULT_SFAPI_TOKEN_URL)


def read_private_key(private_key_path: str) -> bytes:
    with open(private_key_path, "rb") as key_file:
        return key_file.read()


def _token_expiration(token: str) -> int | None:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        expiration = claims.get("exp")
    except (AttributeError, IndexError, json.JSONDecodeError, TypeError, ValueError):
        return None

    if isinstance(expiration, bool) or not isinstance(expiration, (int, float)):
        return None
    return int(expiration)


def _token_cache_directory() -> Path:
    user_id = os.getuid() if hasattr(os, "getuid") else os.getpid()
    return Path(tempfile.gettempdir()) / f"aqdrop-{user_id}"


def _token_cache_path(client_id: str, token_url: str) -> Path:
    identity = f"{client_id}\0{token_url}".encode("utf-8")
    digest = hashlib.sha256(identity).hexdigest()[:24]
    return _token_cache_directory() / f"sfapi-token-{digest}.json"


def _ensure_token_cache_directory() -> Path:
    cache_directory = _token_cache_directory()
    cache_directory.mkdir(mode=0o700, exist_ok=True)

    cache_stat = cache_directory.lstat()
    if not stat.S_ISDIR(cache_stat.st_mode):
        raise OSError(f"SFAPI token cache is not a directory: {cache_directory}")
    if hasattr(os, "getuid") and cache_stat.st_uid != os.getuid():
        raise PermissionError(f"SFAPI token cache has the wrong owner: {cache_directory}")
    if stat.S_IMODE(cache_stat.st_mode) != 0o700:
        cache_directory.chmod(0o700)
    return cache_directory


def _read_cached_sfapi_token(client_id: str, token_url: str) -> str | None:
    cache_path = _token_cache_path(client_id, token_url)
    try:
        cache_stat = cache_path.lstat()
        if not stat.S_ISREG(cache_stat.st_mode):
            return None
        if hasattr(os, "getuid") and cache_stat.st_uid != os.getuid():
            return None
        if stat.S_IMODE(cache_stat.st_mode) & 0o077:
            return None

        cache_entry = json.loads(cache_path.read_text(encoding="utf-8"))
        token = cache_entry.get("access_token")
        expiration = _token_expiration(token) if isinstance(token, str) else None
        if expiration is None or expiration <= time.time() + TOKEN_CACHE_EXPIRY_SKEW_SECONDS:
            cache_path.unlink(missing_ok=True)
            return None
        return token
    except (OSError, json.JSONDecodeError, AttributeError, TypeError):
        return None


def _write_cached_sfapi_token(client_id: str, token_url: str, token: str) -> None:
    expiration = _token_expiration(token)
    if expiration is None or expiration <= time.time() + TOKEN_CACHE_EXPIRY_SKEW_SECONDS:
        return

    cache_directory = _ensure_token_cache_directory()
    cache_path = _token_cache_path(client_id, token_url)
    temporary_path = cache_directory / f".{cache_path.name}.{os.getpid()}.{time.time_ns()}"
    descriptor = None
    try:
        descriptor = os.open(temporary_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as cache_file:
            descriptor = None
            json.dump({"access_token": token, "expires_at": expiration}, cache_file)
        os.replace(temporary_path, cache_path)
        cache_path.chmod(0o600)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary_path.unlink(missing_ok=True)


def invalidate_cached_sfapi_token(client_id: str, token_url: str | None = None) -> None:
    resolved_token_url = token_url or get_token_url()
    try:
        _token_cache_path(client_id, resolved_token_url).unlink(missing_ok=True)
    except OSError:
        pass


def fetch_sfapi_token(client_id: str, private_key_path: str, token_url: str | None = None):
    token_url = token_url or get_token_url()

    try:
        from authlib.integrations.requests_client import OAuth2Session
        from authlib.oauth2.rfc7523 import PrivateKeyJWT
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "authlib is required for SFAPI token fetching. Install it with 'pip install authlib'."
        ) from exc

    private_key = read_private_key(private_key_path)
    session = OAuth2Session(
        client_id,
        private_key,
        PrivateKeyJWT(token_url),
        grant_type="client_credentials",
        token_endpoint=token_url,
    )
    token = session.fetch_token()
    access_token = token.get("access_token")
    if access_token is None:
        raise RuntimeError("SFAPI token response did not contain access_token")
    return access_token


def get_or_fetch_sfapi_token(
    client_id: str,
    private_key_path: str,
    token_url: str | None = None,
    *,
    force_refresh: bool = False,
) -> str:
    resolved_token_url = token_url or get_token_url()
    if not force_refresh:
        cached_token = _read_cached_sfapi_token(client_id, resolved_token_url)
        if cached_token is not None:
            return cached_token

    token = fetch_sfapi_token(client_id, private_key_path, token_url=resolved_token_url)
    try:
        _write_cached_sfapi_token(client_id, resolved_token_url, token)
    except OSError:
        pass
    return token


def refresh_sfapi_token(
    client_id: str,
    private_key_path: str,
    token_url: str | None = None,
) -> str:
    resolved_token_url = token_url or get_token_url()
    invalidate_cached_sfapi_token(client_id, resolved_token_url)
    return get_or_fetch_sfapi_token(
        client_id,
        private_key_path,
        resolved_token_url,
        force_refresh=True,
    )


def resolve_token(
    token: str | None = None,
    client_id: str | None = None,
    private_key_path: str | None = None,
    token_url: str | None = None,
):
    if token is not None:
        return token

    env_token = os.getenv("SFAPI_TOKEN")
    if env_token:
        return env_token

    client_id = client_id or os.getenv("SFAPI_CLIENT_ID")
    private_key_path = private_key_path or os.getenv("SFAPI_PRIVATE_KEY_PATH")

    if client_id and private_key_path:
        return get_or_fetch_sfapi_token(client_id, private_key_path, token_url=token_url)

    if client_id or private_key_path:
        raise NameError(
            "Both SFAPI_CLIENT_ID and SFAPI_PRIVATE_KEY_PATH must be set to fetch an SFAPI token."
        )

    raise NameError(
        "Set SFAPI_TOKEN directly, or provide SFAPI_CLIENT_ID and SFAPI_PRIVATE_KEY_PATH "
        "to fetch an SFAPI token."
    )


def get_network():
    """Returns the value of the AQDROP_HOSTNAME environment variable.

    Raises:
        NameError: If AQDROP_HOSTNAME is not set.
    """
    network = os.getenv("AQDROP_HOSTNAME")
    if network is None:
        raise NameError("Environment variable AQDROP_HOSTNAME must be set!")
    return network
