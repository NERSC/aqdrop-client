#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from aqdrop.actions import aqdrop_util
except ImportError:
    import aqdrop_util
from aqdrop import cli_utils
from aqdrop import defs


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--queue", help="The name of the queue to list jobs for.")
    parser.add_argument("--user", help="The username to list jobs for.")
    parser.add_argument(
        "--firstId",
        type=int,
        help="Reject jobs with ID smaller than this value.",
    )
    parser.add_argument(
        "--status",
        choices=[status.value for status in defs.JobStatus],
        help="The job status to list jobs for.",
    )


def _format_table_row(values, widths, alignments):
    fields = []
    for value, width, alignment in zip(values, widths, alignments):
        if alignment == "right":
            fields.append(str(value).rjust(width))
        else:
            fields.append(str(value).ljust(width))
    return "   ".join(fields).rstrip()


def _print_job_table(jobs):
    headers = list(jobs[0].keys())
    alignments = ["right" if header == "id" else "left" for header in headers]
    rows = []
    for job in jobs:
        row = []
        for header in headers:
            value = job.get(header, "")
            if header == "last_action":
                value = aqdrop_util.format_db_time_pt(value)
            row.append(value)
        rows.append(row)

    widths = [
        max(len(str(header)), *(len(str(row[col_id])) for row in rows))
        for col_id, header in enumerate(headers)
    ]
    print(_format_table_row(headers, widths, alignments))
    print(_format_table_row(["-" * len(header) for header in headers], widths, alignments))
    for row in rows:
        print(_format_table_row(row, widths, alignments))
    print(_format_table_row(headers, widths, alignments))


def _filter_jobs_by_first_id(jobs, first_id):
    if first_id is None:
        return jobs
    return [job for job in jobs if job["id"] >= first_id]


def main(args):

    client = cli_utils.connect_verbose()
    status = defs.JobStatus(args.status) if args.status is not None else None
    jobs = client.query_jobs(queue_name=args.queue, owner_name=args.user, status=status)
    jobs = _filter_jobs_by_first_id(jobs, args.firstId)

    print(f"Found {len(jobs)} jobs.")
    if len(jobs) > 0:
        _print_job_table(jobs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
