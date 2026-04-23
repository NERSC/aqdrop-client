#!/usr/bin/env python3

import argparse
import httpx
import tabulate

from aqdrop import cli_utils
from aqdrop import creds

def trim(s: str, w: int = 80):
    r = ""
    i = 0
    for c in s:
        if i > 0 and i % w == 0:
            r += "\n"
        r += c
        i += 1
        if c == "\n":
            i = 0
    return r



def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--id", help="The ID of the job.")


def main(args):
    try:
        job_id = int(args.id)
    except TypeError:
        print("--id must be an integer.")
        exit()

    c = cli_utils.connect_verbose()

    try:
        job = c.get_job(job_id)
    except httpx.HTTPStatusError as e:
        print(f"Could not get job.")
        print(f"Error {e.response.status_code}: {e.response.json()['detail']}.")
    else:
        job_meta = {k: v for k, v in job.items() if not k in ("input", "output")}
        job_in = job["input"]
        job_out = job["output"]


        print("\nJOB METADATA")
        print(tabulate.tabulate([job_meta.values()], headers=job_meta.keys()))

        if job_in is not None:
            print("\nJOB INPUT")
            print(tabulate.tabulate([[k, trim(str(v))] for k, v in job_in.items()], headers=["field", "value"]))

        if job_out is not None:
            for k, v in job_out.items():
                if type(v) == dict:
                    job_out[k] = tabulate.tabulate([[kk, vv] for kk, vv in v.items()], tablefmt="plain")
            print("\nJOB OUTPUT")
            print(tabulate.tabulate([[k, trim(str(v))] for k, v in job_out.items()], headers=["field", "value"]))

        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
