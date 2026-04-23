#!/usr/bin/env python3

import argparse
import tabulate
import httpx

from aqdrop import cli_utils, defs
from aqdrop import creds

print("Done importing.")


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--queue", help="The name of the queue.")
    parser.add_argument("--default", help="(true/false): if set to true, all users can access the queue unless explicitly set otherwise.")
    parser.add_argument("--limit", help="An integer representing the max number of jobs any user can submit.")
    parser.add_argument("--description", default="", help="A description for the queue.")
    parser.add_argument("--max_qubits", help="The maximum number of qubits available on this chip / simulator.")
    parser.add_argument("--type", help="qpu if jobs will run on quantum hardware, simu if jobs will run on a simulator.")


def main(args):
    default = True if args.default.lower() == "true" else False

    #if args.state == "open":
    #    state = defs.QueueState.OPEN
    #elif args.state == "down":
    #    state = defs.QueueState.DOWN
    #else:
    #    print(f"Unrecognized queue state \"{args.state}.\"\nOptions are {', '.join(s.value for s in defs.QueueState)}.")
    #    exit()

    try:
        limit = int(args.limit)
    except:
        print("--limit must be an integer.")
        exit()

    c = cli_utils.connect_verbose()

    try:
        submitted = c.add_queue(args.queue, default, limit, description=args.description)
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
