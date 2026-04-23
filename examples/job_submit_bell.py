#!/usr/bin/env python3

import argparse
import pprint
import tabulate
import httpx
import tempfile
import base64

from aqdrop import cli_utils
from aqdrop import creds

from qiskit import QuantumCircuit, qpy



def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--queue", default="ideal", help="The name of the queue to submit the Bell state job to.")


def main(args):

    c = cli_utils.connect_verbose()

    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0,1)
    qc.measure(0,0)
    qc.measure(1,1)

    with tempfile.NamedTemporaryFile(delete_on_close=False) as tf:
        qpy.dump(qc, tf)
        tf.close()
        with open(tf.name, 'rb') as tfr:
            b = base64.b64encode(tfr.read())

    job_dd = {
            'qpy': b.decode(),
            'shots': 1024
            }

    try:
        submitted = c.submit_job(args.queue, job_dd)
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
