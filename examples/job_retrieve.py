#!/usr/bin/env python3

"""Retrieve an AQDrop example job and optionally print its packed circuits."""

import argparse
from pathlib import Path
from pprint import pprint
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import aqdrop
from Util_AQDrop import (
    extract_transpiled_qiskit_circuits,
    print_output_counts,
    print_shot_summary,
)


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--id", type=int, required=True, help="The ID of the job to retrieve.")
    parser.add_argument(
        "-v",
        "--verb",
        type=int,
        default=1,
        help="Verbosity level. Use -v1 to print successful counts, -v2 to print all circuits, and -v3 for the full job dump.",
    )


def main(args):
    client = aqdrop.AqdropClient()
    job = client.get_job(job_id=args.id)
    summary = {k: job.get(k) for k in ("id", "owner_name", "queue_name", "status")}
    print(summary)
    status = job.get("status")
    if status == "queued":
        print("no results available yet")
    elif status == "success":
        print_shot_summary(job)
        if args.verb > 0:
            print_output_counts(job.get("output"))

    shots = job.get("input", {}).get("shots", 0)
    if isinstance(shots, list):
        total_shots = sum(shots)
    elif isinstance(shots, int):
        total_shots = shots
    else:
        total_shots = 0

    qpy_blob = job.get("input", {}).get("qpy")
    if qpy_blob is None:
        circuits = []
    else:
        circuits = client.extract_qiskit(qpy_blob)
    print(f"Packed circuits: {len(circuits)}, total requested shots: {total_shots}")

    if args.verb > 1:
        for idx, qc in enumerate(circuits):
            print(f"circuit[{idx}]")
            print(qc)
        if status == "success":
            transpiled_circuits = extract_transpiled_qiskit_circuits(job, client)
            for idx, qc in enumerate(transpiled_circuits):
                print(f"transpiled_circuit[{idx}]")
                print(qc)
    if args.verb > 2:
        pprint(job)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
