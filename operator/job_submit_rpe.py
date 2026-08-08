#!/usr/bin/env python3

"""Submit a batched idle-RPE experiment to an AQDrop queue.

Example:

    ./job_submit_rpe.py --queue IQM --pref_qubit 20 --shots 256
"""

import argparse

import numpy as np
from qiskit import QuantumCircuit

from AqdropUser import AqdropUser


DEPTHS = (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096)
IDLE_DURATION_NS = 100


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument(
        "-q",
        "--queue",
        required=True,
        help="The name of the queue to submit the RPE job to.",
    )
    parser.add_argument(
        "-n",
        "--shots",
        type=int,
        default=256,
        help="The number of shots to submit for each circuit.",
    )
    parser.add_argument(
        "-p",
        "--pref_qubit",
        type=int,
        required=True,
        help="Physical qubit on which to run the RPE measurement.",
    )
    parser.add_argument(
        "--num_idle_steps",
        type=int,
        default=13,
        help="Number of idle depths to submit, from 3 through 13.",
    )
    parser.add_argument(
        "-v",
        "--verb",
        type=int,
        default=1,
        help="Verbosity level. Use values >1 for extra output.",
    )


def make_circuits(depths=DEPTHS):
    circuits = []
    for quadrature, first_rotation in (("cos", "ry"), ("sin", "rx")):
        for depth in depths:
            circuit = QuantumCircuit(1, 1)
            getattr(circuit, first_rotation)(np.pi / 2, 0)
            circuit.barrier()
            circuit.delay(depth * IDLE_DURATION_NS, 0, unit="ns")
            circuit.barrier()
            circuit.ry(-np.pi / 2, 0)
            circuit.measure(0, 0)
            circuit.metadata = {"quadrature": quadrature, "depth": depth}
            circuits.append(circuit)
    return circuits


def main(args):
    assert args.shots > 0, f"shots must be positive, got {args.shots}"
    assert args.pref_qubit >= 0, (
        f"physical qubit must be non-negative, got {args.pref_qubit}"
    )
    assert 3 <= args.num_idle_steps <= len(DEPTHS), (
        f"num_idle_steps must be in [3, {len(DEPTHS)}], "
        f"got {args.num_idle_steps}"
    )

    depths = DEPTHS[: args.num_idle_steps]
    circuits = make_circuits(depths)
    if args.verb > 1:
        print(circuits[-1].draw())

    job_meta = {
        "shots": [args.shots] * len(circuits),
        "comment": "idle RPE measurement",
        "queue_name": args.queue,
        "pref_qubits": [args.pref_qubit],
        "delay_unit": "ns",
    }

    user = AqdropUser(args.verb)
    user.assemble_job_input(circuits, job_meta)
    return user.push_job_input()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()
    main(args)
