#!/usr/bin/env python3

import argparse
import httpx
import tabulate

from aqdrop import cli_utils
from aqdrop import creds


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--skip", default=0, help="The number of members to skip.")
    parser.add_argument("--limit", default=None, help="The maximum number of members to return.")


def main(args, c):

    try:
        skip = int(args.skip)
    except TypeError:
        print("--skip must be an integer.")
        exit()

    try:
        limit = int(args.limit) if args.limit is not None else None
    except TypeError:
        print("--limit must be an integer.")
        exit()

    #c = cli_utils.connect_verbose()
    c = cli_utils.connect_verbose()

    try:
        members = c.list_members(limit=limit, skip=skip)
    except httpx.HTTPStatusError as e:
        print(f"Could not list members.")
        print(f"Error {e.response.status_code}: {e.response.json()['detail']}.")
    else:
        print(tabulate.tabulate([member.values() for member in members], headers=members[0].keys()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
