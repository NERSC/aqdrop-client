#!/usr/bin/env python3

import argparse
import httpx

from aqdrop import cli_utils

def action_info():
    return {"operator": False, "user": False, "description": "Delete a member"}


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("-u", "--name", help="The username of the member to delete.")


def main(args):
    client = cli_utils.connect_verbose()

    try:
        client.delete_member(args.name)
    except httpx.HTTPStatusError as e:
        resp = e.response
        detail = resp.json().get('detail') if 'application/json' in resp.headers.get('content-type', '') else resp.text
        print(f"Could not delete member.")
        print(f"Error {resp.status_code}: {detail}.")
    else:
        print(f"Successfully deleted member {args.name}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
