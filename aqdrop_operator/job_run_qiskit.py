#!/usr/bin/env python3

"""Run one queued AQDrop job on a Qiskit simulator.

Use this script for simulator queues. By default it performs a dry execution;
pass -E/--execJob to run the Qiskit backend and push results back to AQDrop.

The pipeline mirrors job_run_qpu.py, but selects a Qiskit backend instead of
connecting to a QPU. Jobs must come from one of these simulator queues:

    ideal  -> Aer statevector simulator
    noisy  -> Aer simulator built from FakeTorino
"""

import argparse

from .qiskit_operator import QiskitOperator


def _print_execution_table(circL, inputMD, output):
    requested_shots = inputMD["shots"]
    if isinstance(requested_shots, int):
        requested_shots = [requested_shots] * len(circL)
    rows = []
    for circuit_id in range(len(output["shots"])):
        rows.append([
            circuit_id,
            requested_shots[circuit_id],
            output["shots"][circuit_id],
            output["num_qubits"][circuit_id],
            output["num_2q_gates"][circuit_id],
            f"{output['exec_time'][circuit_id]:.2f}",
        ])

    headers = ["id", "shots_asked", "shots_received", "num_qubits", "num_2q_gates", "exec_time"]
    print(" ".join(f"{header:>15}" for header in headers))
    for row in rows:
        print(" ".join(f"{value:>15}" for value in row))


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--id", required=True, help="The ID of the job to run on a Qiskit simulator.")
    parser.add_argument("-v", "--verb", type=int, default=1, help="Verbosity level. Use values >1 for extra output.")
    parser.add_argument("-E", "--execJob", action='store_true', default=False, help="may take long time, test before")


def main(args):
    job_id = int(args.id)

    # 1) instantiate operator (creates its own AQDrop client)
    operator = QiskitOperator(args.verb, args.execJob)

    # 2) pull queued job from DB
    operator.pull_job_input(job_id)

    # 3) disassemble 'input' record into circuits + metadata
    circL, inputMD = operator.parse_job_input()

    # 4) select Qiskit backend from the queue name
    operator.simulator_select()

    # 5) run all circuits on the Qiskit backend
    operator.simulator_run_job()

    if not args.execJob:
        output = {
            "shots": operator.shots,
            "num_qubits": operator.num_qubits,
            "num_2q_gates": operator.num_2q_gates,
            "exec_time": operator.exec_time,
        }
        _print_execution_table(circL, inputMD, output)
        print(f'\njobs NOT executed, only dry execution on {operator.job["queue_name"]}, use -E for running on Qiskit\n')
        return

    # 6) assemble simulator output (counts, shots, exec_time, circ_transp_qpy)
    output = operator.assemble_job_output()

    # 7) push output back to DB
    operator.push_job_output()

    print(f"Job {job_id} dispatch successful.")
    _print_execution_table(circL, inputMD, output)

    if args.verb > 2:
        print("Job dump to follow:")
        from aqdrop.actions import job_dump
        job_dump.main(args)


def cli():
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()
    for arg in vars(args):
        print(arg, getattr(args, arg))

    main(args)


if __name__ == "__main__":
    cli()
