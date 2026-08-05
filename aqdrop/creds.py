from __future__ import annotations

import os

DEFAULT_SFAPI_TOKEN_URL = "https://oidc.nersc.gov/c2id/token"


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
        return fetch_sfapi_token(client_id, private_key_path, token_url=token_url)

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
