#!/usr/bin/env python3

import argparse
import tabulate
import httpx

from aqdrop import cli_utils, defs
from aqdrop import creds


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--queue", help="The name of the queue to update.")
    parser.add_argument("--limit", default=None, help="An integer representing the max number of jobs any user can submit.")
    parser.add_argument("--state", default=None, help="The state of the queue (e.g., open, down, retired).")


def main(args):

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
        elif args.state == "retired":
            state = defs.QueueState.RETIRED
        else:
            print(f"Unrecognized queue state \"{args.state}.\"\nOptions are {', '.join(s.value for s in defs.QueueState)}.")
            exit()

    client = cli_utils.connect_verbose()

    try:
        submitted = client.update_queue(args.queue, limit, state)
    except httpx.HTTPStatusError as e:
        print(f"Could not add queue.")
        resp = e.response
        detail = resp.json().get('detail') if 'application/json' in resp.headers.get('content-type', '') else resp.text
        print(f"Error {resp.status_code}: {detail}.")
    else:
        print(tabulate.tabulate([submitted.values()], headers=submitted.keys()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
