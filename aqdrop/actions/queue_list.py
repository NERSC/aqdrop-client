#!/usr/bin/env python3

import argparse
import tabulate

from aqdrop import cli_utils, defs


def action_info():
    return {"access": "user/admin", "description": "List available queues"}


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "-s",
        "--state",
        choices=[state.value for state in defs.QueueState],
        help="Only list queues in this state.",
    )


def main(args):

    state = defs.QueueState(args.state) if args.state is not None else None

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
