#!/usr/bin/env python3

import argparse
import httpx
import tabulate

from aqdrop import cli_utils
from aqdrop import creds


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--id", help="ID of the job.")


def main(args):
    try:
        job_id = int(args.id)
        if job_id is None:
            print("You must provide a job ID with --id.")
            exit()
    except TypeError:
        print("Job ID must be an integer.")
        exit()

    client = cli_utils.connect_verbose()

    try:
        job = client.check_job(job_id)
    except httpx.HTTPStatusError as e:
        print(f"Could not check job.")
        resp = e.response
        detail = resp.json().get('detail') if 'application/json' in resp.headers.get('content-type', '') else resp.text
        print(f"Error {resp.status_code}: {detail}.")
    else:
        formatted_job = {}
        for k, v in job.items():
            if k == "last_action":
                formatted_job[k] = cli_utils.format_db_time_pt(v)
            else:
                formatted_job[k] = v
        print(tabulate.tabulate([formatted_job.values()], headers=formatted_job.keys()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
