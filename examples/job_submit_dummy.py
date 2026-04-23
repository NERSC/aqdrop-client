#!/usr/bin/env python3

import argparse
import pprint
import tabulate
import httpx

from aqdrop import cli_utils
from aqdrop import creds



def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--queue", help="The name of the queue to submit the dummy job to.")
    parser.add_argument("--task", help="The task dictionary for the dummy job.")


def main(args):

    c = cli_utils.connect_verbose()
    try:
        submitted = c.submit_job(args.queue, args.task)
    except httpx.HTTPStatusError as e:
        print(f"Job submission failed.")
        print(f"Error {e.response.status_code}: {e.response.json()['detail']}.")
    else:
        print(f"Job submission successful; assigned job ID {submitted['id']}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
