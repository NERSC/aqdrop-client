#!/usr/bin/env python3

import argparse
import pprint
import tabulate

from aqdrop import cli_utils
from aqdrop import creds



def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--queue", help="The name of the queue to list jobs for.")


def main(args):

    c = cli_utils.connect_verbose()
    jobs = c.query_jobs(queue_name=args.queue)

    print(f"Found {len(jobs)} jobs.")
    if len(jobs) > 0:
        print(tabulate.tabulate([j.values() for j in jobs], headers=jobs[0].keys()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
