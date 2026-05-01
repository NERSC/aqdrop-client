#!/usr/bin/env python3

"""Submit a small Bell-state example job to an AQDrop queue."""

import argparse
from qiskit import QuantumCircuit

from AqdropUser import AqdropUser


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("-q", "--queue", required=True, help="The name of the queue to submit the Bell state job to.")
    parser.add_argument("-n", "--shots", type=int, default=4000, help="The number of shots to submit with the job.")
    parser.add_argument("-v", "--verb", type=int, default=1, help="Verbosity level. Use values >1 for extra output.")


def circ_bell():
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def main(args):
    qc = circ_bell()
    if args.verb > 1:
        print(qc.draw())

    circuits = [qc]
    job_meta = {"shots": [args.shots], "comment": "my 1st bell job", "queue_name": args.queue, "pref_qubits": None}

    # 1) instantiate user (creates its own AQDrop client)
    user = AqdropUser(args.verb)

    # 2) assemble job_input from circuits + metadata
    user.assemble_job_input(circuits, job_meta)

    # 3) push job_input to DB
    return user.push_job_input()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()
    main(args)
