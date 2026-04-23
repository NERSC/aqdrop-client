#!/usr/bin/env python3

import argparse
import httpx
import tabulate

from aqdrop import cli_utils, defs
from aqdrop import creds



def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--id", help="The ID of the job.")
    parser.add_argument("--status", default="success", help="The status of the job (e.g., success, failed).")
    parser.add_argument("--output", help="The output message for the job.")


def main(args):

    try:
        job_id = int(args.id)
    except TypeError:
        print("--id must be an integer.")
        exit()

    c = cli_utils.connect_verbose()

    try:
        job = c.dispatch_job(job_id, defs.JobStatus(args.status), {"message": args.output})
    except httpx.HTTPStatusError as e:
        print(f"Could not dispatch job.")
        print(f"Error {e.response.status_code}: {e.response.json()['detail']}.")
    else:
        print(tabulate.tabulate([job.values()], headers=job.keys()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
