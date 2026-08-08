#!/usr/bin/env python3

import argparse
import tabulate
import httpx

from aqdrop import cli_utils, defs


def action_info():
    return {"access": "admin", "description": "Update queue settings"}


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("-q", "--queue", help="The name of the queue to update.")
    parser.add_argument("-l", "--limit", default=None, help="An integer representing the max number of jobs any user can submit.")
    parser.add_argument(
        "-s",
        "--state",
        choices=[state.value for state in defs.QueueState],
        help="The new queue state.",
    )
    parser.add_argument("-Q", "--max-qubits", type=int, help="The new maximum qubit count.")
    parser.add_argument(
        "-t",
        "--type",
        choices=[queue_type.value for queue_type in defs.QueueType],
        help="The new queue type.",
    )


def main(args):

    limit = None
    if args.limit is not None:
        try:
            limit = int(args.limit)
        except:
            print("--limit must be an integer.")
            exit()

    state = defs.QueueState(args.state) if args.state is not None else None
    queue_type = defs.QueueType(args.type) if args.type is not None else None

    client = cli_utils.connect_verbose()

    try:
        submitted = client.update_queue(
            args.queue,
            new_limit=limit,
            new_state=state,
            new_max_qubits=args.max_qubits,
            new_type=queue_type,
        )
    except httpx.HTTPStatusError as e:
        print("Could not update queue.")
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
