#!/usr/bin/env python3

"""Smoke-test AQDrop member listing against the dev API hostname."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aqdrop


DEFAULT_HOST = "https://aqdrop-api-dev.lbl-b59.org"
DEFAULT_CLIENT_ID = "qn5djiwvs3dnm"
DEFAULT_PRIVATE_KEY_PATH = "/var/home_ext/aqdrop/private_key.pem"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test AQDrop member listing with SFAPI client credentials."
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"AQDrop API base URL. Defaults to {DEFAULT_HOST}.",
    )
    parser.add_argument(
        "--client-id",
        default=DEFAULT_CLIENT_ID,
        help=f"SFAPI client ID. Defaults to {DEFAULT_CLIENT_ID}.",
    )
    parser.add_argument(
        "--private-key-path",
        default=DEFAULT_PRIVATE_KEY_PATH,
        help=f"Path to the SFAPI private key PEM file. Defaults to {DEFAULT_PRIVATE_KEY_PATH}.",
    )
    parser.add_argument(
        "--token-url",
        default=None,
        help="Optional SFAPI token endpoint override.",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS certificate verification for the AQDrop API request.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    print("Fetching bearer token with SFAPI client credentials.")
    print(f"client_id={args.client_id}")
    print(f"private_key_path={args.private_key_path}")

    try:
        client = aqdrop.AqdropClient(
            host=args.host,
            client_id=args.client_id,
            private_key_path=args.private_key_path,
            token_url=args.token_url,
        )
        if args.insecure:
            client._client = httpx.Client(base_url=args.host.rstrip("/"), timeout=10, verify=False)

        members = client.list_members()
    except FileNotFoundError as exc:
        print(f"Private key file not found: {exc}")
        return 1
    except httpx.HTTPStatusError as exc:
        response = exc.response
        detail = response.text.strip()
        print(f"AQDrop API request failed: HTTP {response.status_code}")
        if detail:
            print(detail)
        return 1
    except Exception as exc:  # pragma: no cover - manual smoke test script
        print(f"Authentication or request failed: {exc}")
        return 1

    print(f"Authenticated successfully against {args.host}")
    print(f"Retrieved {len(members)} member(s).")
    for member in members:
        print(
            f"- name={member.get('name')} "
            f"admin={member.get('is_admin')} "
            f"operator={member.get('is_operator')} "
            f"suspended={member.get('is_suspended')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
