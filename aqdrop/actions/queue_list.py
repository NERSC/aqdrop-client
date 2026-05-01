#!/usr/bin/env python3

import argparse
import tabulate

from aqdrop import cli_utils, defs
from aqdrop import creds


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--state", default=None, help="The state of the queues to list (e.g., open, down).")


def main(args):

    if args.state == "open":
        state = defs.QueueState.OPEN
    elif args.state == "down":
        state = defs.QueueState.DOWN
    elif args.state is not None:
        print(f"Unrecognized queue state \"{args.state}.\"\nOptions are {', '.join(s.value for s in defs.QueueState)}.")
        exit()
    else: state = None

    client = cli_utils.connect_verbose()
    queues = client.list_queues(state)

    print(f"Found {len(queues)} queues.")
    if len(queues) > 0:
        print(tabulate.tabulate([q.values() for q in queues], headers=queues[0].keys()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
