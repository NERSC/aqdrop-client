#!/usr/bin/env python3

"""Retrieve an AQDrop example job and optionally print its packed circuits."""

import argparse
from pprint import pprint

import aqdrop
from Util_AQDrop import extract_qiskit_circuits


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--id", type=int, required=True, help="The ID of the job to retrieve.")
    parser.add_argument("-v", "--verb", type=int, default=1, help="Verbosity level. Use -v2 to print all circuits and -v3 for the full job dump.")


def main(args):
    client = aqdrop.AqdropClient()
    job = client.get_job(job_id=args.id)
    summary = {k: job.get(k) for k in ("id", "owner_name", "queue_name", "status")}
    print(summary)
    if job.get("status") == "queued":
        print("no results available yet")
    circuits = extract_qiskit_circuits(job)
    if args.verb > 1:
        for idx, qc in enumerate(circuits):
            print(f"circuit[{idx}]")
            print(qc)
    if args.verb > 2:
        pprint(job)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
