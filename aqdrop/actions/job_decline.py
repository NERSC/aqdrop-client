#!/usr/bin/env python3

import argparse
import httpx

from aqdrop import cli_utils, defs
from aqdrop import creds



def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--id", help="The ID of the job.")
    parser.add_argument("--output", help="The output message for the job.")


def main(args):

    try:
        job_id = int(args.id)
    except TypeError:
        print("--id must be an integer.")
        exit()

    client = cli_utils.connect_verbose()

    try:
        job = client.dispatch_job(job_id, defs.JobStatus.DECLINED, {"message": args.output})
    except httpx.HTTPStatusError as e:
        print(f"Could not dispatch job.")
        resp = e.response
        detail = resp.json().get('detail') if 'application/json' in resp.headers.get('content-type', '') else resp.text
        print(f"Error {resp.status_code}: {detail}.")
    else:
        job_meta = {k: v for k, v in job.items() if k not in ("input", "output")}
        cli_utils.print_job_table([job_meta])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
