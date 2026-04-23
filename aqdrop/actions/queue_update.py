#!/usr/bin/env python3

import argparse
import tabulate
import httpx

from aqdrop import cli_utils, defs
from aqdrop import creds


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--queue", help="The name of the queue to update.")
    parser.add_argument("--new_name", default=None, help="The new name for the queue.")
    parser.add_argument("--default", default=None, help="(true/false): if set to true, all users can access the queue unless explicitly set otherwise.")
    parser.add_argument("--limit", default=None, help="An integer representing the max number of jobs any user can submit.")
    parser.add_argument("--state", default=None, help="The state of the queue (e.g., open, down).")


def main(args):

    default = None
    if args.default is not None:
        default = True if args.default.lower() == "true" else False

    limit = None
    if args.limit is not None:
        try:
            limit = int(args.limit)
        except:
            print("--limit must be an integer.")
            exit()

    state = None
    if args.state is not None:
        if args.state == "open":
            state = defs.QueueState.OPEN
        elif args.state == "down":
            state = defs.QueueState.DOWN
        else:
            print(f"Unrecognized queue state \"{args.state}.\"\nOptions are {', '.join(s.value for s in defs.QueueState)}.")
            exit()

    c = cli_utils.connect_verbose()

    try:
        submitted = c.update_queue(args.queue, args.new_name, default, limit, state)
    except httpx.HTTPStatusError as e:
        print(f"Could not add queue.")
        print(f"Error {e.response.status_code}: {e.response.json()['detail']}.")
    else:
        print(tabulate.tabulate([submitted.values()], headers=submitted.keys()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
