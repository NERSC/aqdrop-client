#!/usr/bin/env python3

import argparse
import httpx
import tabulate

from aqdrop import AqdropClient, connect_verbose, defs
from aqdrop import creds


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--name", help="The username of the member.")
    parser.add_argument("--operator", default=None, help="(true/false): if set to true, the user is an operator.")
    parser.add_argument("--admin", default=None, help="(true/false): if set to true, the user is an admin.")
    parser.add_argument("--suspended", default=None, help="(true/false): if set to true, the user is suspended.")


def main(args):

    operator = args.operator
    if operator is None:
        pass
    elif operator.lower() == "true":
        operator = True
    elif operator.lower() == "false":
        operator = False
    else:
        print(f"Unrecognized operator setting \"{args.operator}.\"\nOptions are true, false.")
        exit()

    admin = args.admin
    if admin is None:
        pass
    elif admin.lower() == "true":
        admin = True
    elif admin.lower() == "false":
        admin = False
    else:
        print(f"Unrecognized admin setting \"{args.admin}.\"\nOptions are true, false.")
        exit()

    suspended = args.suspended
    if suspended is None:
        pass
    elif suspended.lower() == "true":
        suspended = True
    elif suspended.lower() == "false":
        suspended = False
    else:
        print(f"Unrecognized suspended setting \"{args.suspended}.\"\nOptions are true, false.")
        exit()

    c = connect_verbose()

    try:
        queues = c.update_member_perms(args.name, is_admin=admin, is_operator=operator, is_suspended=suspended)
    except httpx.HTTPStatusError as e:
        print(f"Could not update member permissions.")
        print(f"Error {e.response.status_code}: {e.response.json()['detail']}.")
    else:
        print("OK.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
