#!/usr/bin/env python3

import argparse
import pprint
import httpx

from aqdrop import cli_utils
from aqdrop import creds


def add_args(parser):
    parser.add_argument("--name", help="The username of the new member.")
    parser.add_argument("--email", default=None, help="The email address of the new member.")
    parser.add_argument("--operator", action="store_true", help="Set this flag to make the new user an operator.")
    parser.add_argument("--admin", action="store_true", help="Set this flag to make the new user an admin.")


def main(args):
    c = cli_utils.connect_verbose()

    try:
        output = c.create_member(args.name, args.email)
        c.update_member_perms(args.name, args.admin, args.operator)
    except httpx.HTTPStatusError as e:
        print(f"Could not create member.")
        resp = e.response
        detail = resp.json().get('detail') if 'application/json' in resp.headers.get('content-type', '') else resp.text
        print(f"Error {resp.status_code}: {detail}")
    else:
        # print out properly formatted .creds file to stdout so we can route it into a file
        print("#!/usr/bin/bash")
        print(f"export AQDROP_USERNAME={args.name}")
        print(f"export AQDROP_PASSWORD={output['password']}")
        print(f"export AQDROP_EMAIL={args.email}")
        print(f"export AQDROP_HOSTNAME={creds.get_network()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
