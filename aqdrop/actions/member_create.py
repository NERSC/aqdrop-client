#!/usr/bin/env python3

import argparse
import httpx

from aqdrop import AqdropClient
from aqdrop import creds


def action_info():
    return {"operator": False, "user": False, "description": "Create a new member"}


def add_args(parser):
    parser.add_argument("-u", "--name", help="The username of the new member.")
    parser.add_argument("-e", "--email", default=None, help="The email address of the new member.")
    parser.add_argument("-o", "--operator", action="store_true", help="Set this flag to make the new user an operator.")
    parser.add_argument("-a", "--admin", action="store_true", help="Set this flag to make the new user an admin.")


def main(args):
    client = AqdropClient()

    try:
        output = client.create_member(args.name, args.email)
        client.update_member_perms(args.name, args.admin, args.operator)
    except httpx.HTTPStatusError as e:
        print(f"Could not create member.")
        resp = e.response
        detail = resp.json().get('detail') if 'application/json' in resp.headers.get('content-type', '') else resp.text
        print(f"Error {resp.status_code}: {detail}")
    else:
        # print out properly formatted .creds file to stdout so we can route it into a file
        print("#!/usr/bin/bash")
        print(f"export AQDROP_USERNAME={args.name}")
        print("export NERSC_OIDC_TOKEN=<your-nersc-token>")
        print(f"export AQDROP_HOSTNAME={creds.get_network()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
