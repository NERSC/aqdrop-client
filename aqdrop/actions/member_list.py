#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path

import httpx
import tabulate


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aqdrop import cli_utils
from aqdrop import creds


MEMBER_COLUMNS = ("name", "is_operator", "is_admin", "email", "id", "created_at", "updated_at")
MEMBER_HEADERS = ("name", "operator", "admin", "email", "id", "created_at", "updated_at")


def action_info():
    return {"operator": True, "user": False, "description": "List all members"}


def add_args(parser: argparse.ArgumentParser):
    pass


def _format_member_row(member):
    row = []
    for column in MEMBER_COLUMNS:
        value = member.get(column, "")
        if column in ("created_at", "updated_at"):
            value = cli_utils.format_db_time_pt(value)
        row.append(value)
    return row


def _print_member_table(members):
    rows = [_format_member_row(member) for member in members]
    print(tabulate.tabulate(rows, headers=MEMBER_HEADERS))


def main(args):
    client = cli_utils.connect_verbose()

    try:
        members = client.list_members()
    except httpx.HTTPStatusError as e:
        print(f"Could not list members.")
        resp = e.response
        detail = resp.json().get('detail') if 'application/json' in resp.headers.get('content-type', '') else resp.text
        print(f"Error {resp.status_code}: {detail}.")
    else:
        _print_member_table(members)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
