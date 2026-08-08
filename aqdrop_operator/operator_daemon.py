#!/usr/bin/env python3

"""Poll AQDrop for queued jobs and execute them with the proper operator.

Simulator queues are sent to job_run_qiskit.py; all other queues are sent to
job_run_qpu.py. The daemon sleeps when no queued jobs are available and stops
on the first runner error.
"""

import argparse
import time
from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

if not __package__:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "aqdrop_operator"

from aqdrop import AqdropClient, defs


SIMU_QUEUES = ("ideal", "noisy")
PT_TIMEZONE = ZoneInfo("America/Los_Angeles")


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "sleepSecArg",
        nargs="?",
        type=int,
        help="Seconds to sleep when no queued jobs are found.",
    )
    parser.add_argument(
        "--sleepSec",
        type=int,
        default=20,
        help="Seconds to sleep when no queued jobs are found.",
    )
    parser.add_argument(
        "-v",
        "--verb",
        type=int,
        default=1,
        help="Verbosity level passed to job runners.",
    )
    parser.add_argument(
        "--owner",
        help="Only execute queued jobs owned by this NERSC username.",
    )
    parser.add_argument(
        "--idRange",
        nargs="+",
        metavar="BOUND",
        help=(
            "Only execute queued jobs with IDs in an inclusive range. "
            "Use two bounds, e.g. '12 56', 'any 23', or '67 any'. "
            "'67 and' is also accepted as an open upper bound. "
            "'none' disables the filter."
        ),
    )


def _format_last_action(last_action):
    if last_action is None:
        return ""

    if isinstance(last_action, datetime):
        action_time = last_action
    elif isinstance(last_action, str):
        normalized_time = last_action
        if normalized_time.endswith("Z"):
            normalized_time = normalized_time[:-1] + "+00:00"
        try:
            action_time = datetime.fromisoformat(normalized_time)
        except ValueError:
            return last_action
    else:
        return str(last_action)

    if action_time.tzinfo is None or action_time.tzinfo.utcoffset(action_time) is None:
        action_time = action_time.replace(tzinfo=timezone.utc)
    action_time = action_time.astimezone(PT_TIMEZONE)

    return action_time.strftime("%Y-%m-%d %H:%M:%S %Z")


def _get_shot_stats(job_input):
    if not isinstance(job_input, dict):
        return "", ""

    shots = job_input.get("shots")
    if isinstance(shots, list):
        return len(shots), sum(shots)
    return "", ""


def _add_table_fields(client, jobs):
    table_jobs = []
    for job in jobs:
        job_for_table = dict(job)
        if "input" not in job_for_table:
            job_details = client.get_job(job["id"])
            job_for_table["input"] = job_details.get("input", {})
        num_circuits, tot_shots = _get_shot_stats(job_for_table.get("input"))
        job_for_table["num_circuits"] = num_circuits
        job_for_table["tot_shots"] = tot_shots
        table_jobs.append(job_for_table)
    return table_jobs


def _format_table_row(values, widths, alignments):
    fields = []
    for value, width, alignment in zip(values, widths, alignments):
        if alignment == "right":
            fields.append(str(value).rjust(width))
        else:
            fields.append(str(value).ljust(width))
    return "   ".join(fields).rstrip()


def _print_job_table(jobs, include_title=True):
    print()
    if include_title:
        print("Queued jobs found:")

    headers = ("jobId", "user", "queue", "last_action", "circ", "tot_shots")
    alignments = ("right", "left", "left", "left", "right", "right")
    rows = []
    for job in jobs:
        rows.append(
            (
                job["id"],
                job.get("owner_name", ""),
                job["queue_name"],
                _format_last_action(job.get("last_action")),
                job.get("num_circuits", ""),
                job.get("tot_shots", ""),
            )
        )

    widths = [
        max(len(str(header)), *(len(str(row[col_id])) for row in rows))
        for col_id, header in enumerate(headers)
    ]
    print(_format_table_row(headers, widths, alignments))
    print(_format_table_row(tuple("-" * len(header) for header in headers), widths, alignments))
    for row in rows:
        print(_format_table_row(row, widths, alignments))
    print()


def _filter_jobs_by_owner(jobs, owner_name):
    if owner_name is None:
        return jobs
    return [job for job in jobs if job.get("owner_name") == owner_name]


def _parse_id_bound(bound, bound_name):
    normalized = bound.lower()
    open_markers = ("any", "none", "*", "-")
    if normalized in open_markers or (bound_name == "upper" and normalized == "and"):
        return None

    try:
        job_id = int(bound)
    except ValueError:
        raise SystemExit(f"--idRange {bound_name} bound must be an integer or 'any', got {bound!r}.")

    if job_id < 0:
        raise SystemExit(f"--idRange {bound_name} bound must be non-negative, got {job_id}.")
    return job_id


def _parse_id_range(id_range):
    if id_range is None:
        return None
    if len(id_range) == 1 and id_range[0].lower() == "none":
        return None
    if len(id_range) != 2:
        raise SystemExit("--idRange expects two bounds, e.g. '12 56', 'any 23', or '67 any'.")

    min_id = _parse_id_bound(id_range[0], "lower")
    max_id = _parse_id_bound(id_range[1], "upper")
    if min_id is not None and max_id is not None and min_id > max_id:
        raise SystemExit(f"--idRange lower bound {min_id} is greater than upper bound {max_id}.")
    return min_id, max_id


def _filter_jobs_by_id_range(jobs, id_range):
    if id_range is None:
        return jobs

    min_id, max_id = id_range
    filtered_jobs = []
    for job in jobs:
        job_id = job["id"]
        if min_id is not None and job_id < min_id:
            continue
        if max_id is not None and job_id > max_id:
            continue
        filtered_jobs.append(job)
    return filtered_jobs


def _format_id_range(id_range):
    if id_range is None:
        return ""

    min_id, max_id = id_range
    if min_id is None and max_id is None:
        return "all job IDs"
    if min_id is None:
        return f"jobId <= {max_id}"
    if max_id is None:
        return f"jobId >= {min_id}"
    return f"{min_id} <= jobId <= {max_id}"


def _print_filter_summary(total_jobs, owner_jobs_count, filtered_jobs_count, owner_name, id_range):
    if owner_name is None and id_range is None:
        return

    summary = [f"{total_jobs} Queued jobs found"]
    if owner_name is not None:
        summary.append(f"{owner_jobs_count} belongs to owner {owner_name}")
    if id_range is not None:
        summary.append(f"{filtered_jobs_count} pass idRange {_format_id_range(id_range)}")
    print(", ".join(summary))


def _print_no_jobs_message(total_jobs, owner_jobs_count, owner_name, id_range, sleep_sec):
    if total_jobs == 0:
        print(f"No queued jobs found. Sleeping {sleep_sec} seconds.")
    elif owner_name is not None and owner_jobs_count == 0:
        print(f"No queued jobs for owner {owner_name}. Sleeping {sleep_sec} seconds.")
    else:
        print(f"No queued jobs passed filters. Sleeping {sleep_sec} seconds.")


def _run_job(job, verb: int):
    from . import job_run_qiskit, job_run_qpu

    args = SimpleNamespace(id=str(job["id"]), verb=verb, execJob=True)
    if job["queue_name"] in SIMU_QUEUES:
        job_run_qiskit.main(args)
    else:
        job_run_qpu.main(args)


def main(args):
    client = AqdropClient()
    executed_jobs = 0
    sleep_sec = args.sleepSecArg if args.sleepSecArg is not None else args.sleepSec
    owner_name = getattr(args, "owner", None)
    id_range = _parse_id_range(getattr(args, "idRange", None))

    while True:
        queued_jobs = client.query_jobs(status=defs.JobStatus.QUEUED)
        if owner_name is None:
            jobs = queued_jobs
            owner_jobs_count = None
        else:
            jobs = _filter_jobs_by_owner(queued_jobs, owner_name)
            owner_jobs_count = len(jobs)
        jobs = _filter_jobs_by_id_range(jobs, id_range)
        _print_filter_summary(len(queued_jobs), owner_jobs_count, len(jobs), owner_name, id_range)

        if len(jobs) == 0:
            _print_no_jobs_message(len(queued_jobs), owner_jobs_count, owner_name, id_range, sleep_sec)
            time.sleep(sleep_sec)
            continue

        table_jobs = _add_table_fields(client, jobs)
        _print_job_table(table_jobs, include_title=owner_name is None and id_range is None)

        for job in jobs:
            _run_job(job, args.verb)
            executed_jobs += 1
            print(f"Executed jobs so far: {executed_jobs}")
            time.sleep(5)


def cli():
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)


if __name__ == "__main__":
    cli()
