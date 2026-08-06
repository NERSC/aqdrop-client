#!/usr/bin/env python3

"""Submit a batched T1 experiment to an AQDrop queue.

Example:

    ./job_submit_t1.py --queue IQM --pref_qubit 20 --shots 2000
"""

import argparse
from qiskit import QuantumCircuit

from AqdropUser import AqdropUser


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("-q", "--queue", required=True, help="The name of the queue to submit the T1 job to.")
    parser.add_argument("-n", "--shots", type=int, default=2000, help="The number of shots to submit with the job.")
    parser.add_argument(
        "-p",
        "--pref_qubit",
        type=int,
        required=True,
        help="Physical qubit on which to run the T1 measurement.",
    )
    parser.add_argument("-v", "--verb", type=int, default=1, help="Verbosity level. Use values >1 for extra output.")


DELAYS_NS = tuple(range(0, 126_000, 3_000))


def make_circuits(delays_ns=DELAYS_NS):
    circuits = []
    for delay_ns in delays_ns:
        circuit = QuantumCircuit(1, 1)
        circuit.x(0)
        circuit.barrier()
        circuit.delay(delay_ns, 0, unit="ns")
        circuit.barrier()
        circuit.measure(0, 0)
        circuit.metadata = {"delay_ns": delay_ns}
        circuits.append(circuit)
    return circuits


def main(args):
    assert args.shots > 0, f"shots must be positive, got {args.shots}"
    assert args.pref_qubit >= 0, (
        f"physical qubit must be non-negative, got {args.pref_qubit}"
    )

    circuits = make_circuits()
    if args.verb > 1:
        print(circuits[-1].draw())

    job_meta = {
        "shots": [args.shots] * len(circuits),
        "comment": "T1 measurement",
        "queue_name": args.queue,
        "pref_qubits": [args.pref_qubit],
        "delay_unit": "ns",
    }

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
