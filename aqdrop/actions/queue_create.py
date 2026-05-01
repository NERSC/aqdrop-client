#!/usr/bin/env python3

import argparse
import tabulate
import httpx

from aqdrop import cli_utils, defs
from aqdrop import creds


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--queue", help="The name of the queue.")
    parser.add_argument("--default", help="(true/false): if set to true, all users can access the queue unless explicitly set otherwise.")
    parser.add_argument("--limit", help="An integer representing the max number of jobs any user can submit.")
    parser.add_argument("--description", default="", help="A description for the queue.")
    parser.add_argument("--max_qubits", help="The maximum number of qubits available on this chip / simulator.")
    parser.add_argument("--type", help="qpu if jobs will run on quantum hardware, simu if jobs will run on a simulator.")


def main(args):
    default = True if args.default.lower() == "true" else False

    if args.type == "qpu":
        queue_type = defs.QueueType.QPU
    elif args.type == "simu":
        queue_type = defs.QueueType.SIMU
    else:
        print(f"Unrecognized queue type \"{args.type}.\"\nOptions are {', '.join(s.value for s in defs.QueueType)}.")
        exit()

    try:
        limit = int(args.limit)
    except:
        print("--limit must be an integer.")
        exit()

    try:
        max_qubits = int(args.max_qubits)
    except:
        print("--max_qubits must be an integer.")
        exit()

    client = cli_utils.connect_verbose()

    try:
        submitted = client.add_queue(args.queue, default, limit, queue_type, max_qubits, description=args.description)
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
