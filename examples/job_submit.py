#!/usr/bin/env python3

"""Submit a small example job (Bell + SPAM + random angles) to an AQDrop queue."""

import argparse
import numpy as np
from pprint import pprint
from qiskit import QuantumCircuit

from AqdropUser import AqdropUser, print_circuit_table


def add_args(parser: argparse.ArgumentParser):
    p = parser.add_argument
    p('-q',"--queue", default="X6Y3", help="Queue/chip name.")
    p("-n", "--shots", type=int, default=1024, help="Base shot count (see per-circuit scaling in main).")
    p("--pref_qubits", type=int, nargs="+", default=[1, 2], metavar="2 0 3", help="Preferred qubit list, or None")
    p("-v", "--verb", type=int, default=1, help="Verbosity; use >1 for extra output.")
    p("-E", "--execJob", action="store_true", help="Submit job; default is dry preview only.")


def circ_bell():
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(0, 0)
    qc.measure(1, 1)
    return qc


def circ_tens2(th0, th1):
    qc = QuantumCircuit(2)
    qc.rx(th0, 0)
    qc.ry(th1, 1)
    qc.measure_all()
    return qc


def main(args):
    for arg in vars(args):
        print(arg, getattr(args, arg))

    if args.verb > 1:
        print(circ_bell())
        print(circ_tens2(0.3, -0.2))

    # prepare list of circuits to be executed
    # this example: Bell-state, 4 SPAM circ, 2 random angles circ
    circL = [circ_bell(), circ_tens2(0, 0), circ_tens2(0, np.pi),
             circ_tens2(np.pi, 0), circ_tens2(np.pi, np.pi), circ_tens2(0.8, -2.5)]

    shotL = [args.shots] + 4*[4*args.shots] + [100]
    nCirc = len(circL)
    job_meta = {"shots": shotL, "comment": "bell job and SPAM measurement", "queue_name": args.queue, "pref_qubits": args.pref_qubits}

    print('M: execution-ready %d circuits to AQDrop queue=%s' % (nCirc, args.queue))
    if not args.execJob:
        print_circuit_table(circL, job_meta)
        pprint(job_meta)
        print('\nNO execution of circuits, use -E to execute the job\n')
        exit(0)

    # 1) instantiate user (creates its own AQDrop client)
    user = AqdropUser(args.verb)

    # 2) assemble job_input from circuits + metadata
    user.assemble_job_input(circL, job_meta)

    # 3) push job_input to DB
    user.push_job_input()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()

    main(args)
