#!/usr/bin/env python3

"""Retrieve an AQDrop example job and optionally print its packed circuits."""

import argparse
from pprint import pprint

from AqdropUser import AqdropUser


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
    # 1) instantiate user (creates its own AQDrop client)
    user = AqdropUser(args.verb)

    # 2) pull job from DB (input always present, output if available)
    job = user.pull_job(args.id)

    # 3) parse job into circuits, input metadata, output, transpiled circuits
    circL, inputMD, output, transpiledL = user.parse_job()

    status = job["status"]
    if status == "queued":
        print("no results available yet")
    elif status == "success":
        user.print_shot_summary()
        print(f"tot_exec_time={output['tot_exec_time']:.1f} sec")
        print(f"received tot_shots={output['tot_shots']}")
        print(f"calib_ver={output['calib_ver']}")
        print(f"exec_date={output['exec_date']}")
        if args.verb > 0:
            user.print_output_counts()

    total_shots = sum(inputMD["shots"])
    print(f"Packed circuits: {len(circL)}, total requested shots: {total_shots}")

    if args.verb > 1:
        for idx, qc in enumerate(circL):
            print(f"circuit[{idx}]")
            print(qc)
        if transpiledL:
            for idx, qc in enumerate(transpiledL):
                print(f"transpiled_circuit[{idx}]")
                print(qc)
    if args.verb > 2:
        pprint(job)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
