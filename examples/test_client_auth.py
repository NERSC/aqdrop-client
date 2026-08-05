#!/usr/bin/env python3

"""Smoke-test AQDrop client auth with SFAPI credentials or a direct token."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aqdrop


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test AQDrop client authentication and perform a simple API request."
    )
    parser.add_argument(
        "--host",
        default=os.getenv("AQDROP_HOSTNAME"),
        help="AQDrop API base URL. Defaults to AQDROP_HOSTNAME.",
    )
    parser.add_argument(
        "--token",
        default=os.getenv("SFAPI_TOKEN"),
        help="Use an already issued bearer token instead of fetching one.",
    )
    parser.add_argument(
        "--client-id",
        default=os.getenv("SFAPI_CLIENT_ID"),
        help="SFAPI client ID. Defaults to SFAPI_CLIENT_ID.",
    )
    parser.add_argument(
        "--private-key-path",
        default=os.getenv("SFAPI_PRIVATE_KEY_PATH"),
        help="Path to the SFAPI private key PEM file. Defaults to SFAPI_PRIVATE_KEY_PATH.",
    )
    parser.add_argument(
        "--token-url",
        default=os.getenv("AQDROP_SFAPI_TOKEN_URL"),
        help="Optional SFAPI token endpoint override.",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=5,
        help="How many jobs to request for the smoke test.",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Skip TLS certificate verification for the AQDrop API request.",
    )
    return parser.parse_args()


def build_client(args: argparse.Namespace) -> aqdrop.AqdropClient:
    if not args.host:
        raise SystemExit("Set --host or AQDROP_HOSTNAME before running this script.")

    if args.token:
        print("Using direct bearer token authentication.")
        client = aqdrop.AqdropClient(host=args.host, token=args.token)
        if args.insecure:
            client._client = httpx.Client(base_url=args.host.rstrip("/"), timeout=10, verify=False)
        return client

    if not args.client_id or not args.private_key_path:
        raise SystemExit(
            "Set --token, or provide both --client-id and --private-key-path, "
            "or set SFAPI_CLIENT_ID and SFAPI_PRIVATE_KEY_PATH."
        )

    print("Fetching bearer token with SFAPI client credentials.")
    print(f"client_id={args.client_id}")
    print(f"private_key_path={args.private_key_path}")
    client = aqdrop.AqdropClient(
        host=args.host,
        client_id=args.client_id,
        private_key_path=args.private_key_path,
        token_url=args.token_url,
    )
    if args.insecure:
        client._client = httpx.Client(base_url=args.host.rstrip("/"), timeout=10, verify=False)
    return client


def main() -> int:
    args = parse_args()
    client = build_client(args)

    try:
        jobs = client.query_jobs(max_jobs=args.max_jobs)
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
    print(f"Retrieved {len(jobs)} job(s).")
    for job in jobs:
        job_id = job.get("id")
        status = job.get("status")
        owner = job.get("owner_name")
        queue = job.get("queue_name")
        print(f"- id={job_id} status={status} owner={owner} queue={queue}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
