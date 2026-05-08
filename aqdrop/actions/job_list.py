#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from aqdrop import cli_utils
from aqdrop import defs


def action_info():
    return {"operator": True, "user": True, "description": "List and filter jobs"}


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("-I", "--id-min", type=int, help="Minimum job ID.")
    parser.add_argument("-A", "--id-max", type=int, help="Maximum job ID.")
    parser.add_argument("-q", "--queue", help="The name of the queue to list jobs for.")
    parser.add_argument("-u", "--user", help="The username to list jobs for.")
    parser.add_argument(
        "-s",
        "--status",
        choices=[status.value for status in defs.JobStatus],
        help="The job status to list jobs for.",
    )
    parser.add_argument("-l", "--max-jobs", type=int, help="Maximum number of jobs to return.")
    parser.add_argument("-C", "--created-min", help="Filter jobs created after this time.")
    parser.add_argument("-X", "--created-max", help="Filter jobs created before this time.")
    parser.add_argument("-r", "--reverse", action="store_true", help="Reverse the order of results.")


def main(args):

    client = cli_utils.connect_verbose()
    status = defs.JobStatus(args.status) if args.status is not None else None
    jobs = client.query_jobs(
        id_min=args.id_min,
        id_max=args.id_max,
        queue_name=args.queue,
        owner_name=args.user,
        status=status,
        max_jobs=args.max_jobs,
        created_min=args.created_min,
        created_max=args.created_max,
        reverse=args.reverse
    )

    print(f"Found {len(jobs)} jobs.")
    if len(jobs) > 0:
        cli_utils.print_job_table(jobs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
