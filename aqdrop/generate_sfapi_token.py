"""Generate an SFAPI bearer token from file-based client credentials."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import creds


def _read_client_id(path: Path) -> str:
    client_id = path.read_text(encoding="utf-8").strip()
    if not client_id:
        raise ValueError(f"client ID file is empty: {path}")
    if any(character.isspace() for character in client_id):
        raise ValueError(f"client ID file must contain one value without whitespace: {path}")
    return client_id


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an SFAPI bearer token from a client ID file and private key file."
    )
    parser.add_argument(
        "--client-id-file",
        required=True,
        type=Path,
        help="File containing the SFAPI client ID.",
    )
    parser.add_argument(
        "--private-key-file",
        required=True,
        type=Path,
        help="PEM file containing the matching SFAPI private key.",
    )
    parser.add_argument(
        "--token-url",
        help=(
            "SFAPI token endpoint override. Defaults to AQDROP_SFAPI_TOKEN_URL or "
            f"{creds.DEFAULT_SFAPI_TOKEN_URL}."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        client_id = _read_client_id(args.client_id_file)
        if not args.private_key_file.is_file():
            raise ValueError(f"private key file does not exist: {args.private_key_file}")
        token = creds.fetch_sfapi_token(
            client_id,
            str(args.private_key_file),
            token_url=args.token_url,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    print(token)


if __name__ == "__main__":
    main()
