#!/usr/bin/env python3

"""Run one queued AQDrop job on a QPU.

Use this script on the operator workstation for jobs submitted to hardware
queues. By default it performs a dry execution; pass -E/--execJob to run on
the QPU and push results back to AQDrop.

The pipeline mirrors the submit-side breakdown in
AQDrop/examples/job_submit.py: each step is a single, clearly named call.
"""

import argparse
import logging
import tabulate

if not __package__:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "aqdrop_operator"

from .aqdrop_operator import AqdropOperator

logging.getLogger("qiskit.passmanager").setLevel(logging.WARNING)


def _print_execution_table(circL, inputMD, output):
    print("pref_qubits", inputMD.get("pref_qubits"))
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

    print(tabulate.tabulate(
        rows,
        headers=["id", "shots_asked", "shots_received", "num_qubits", "num_2q_gates", "exec_time"],
        tablefmt="github",
    ))


def add_args(parser: argparse.ArgumentParser):
    parser.add_argument("--id", required=True, help="The ID of the job to run on the QPU.")
    parser.add_argument("-v", "--verb", type=int, default=1, help="Verbosity level. Use values >1 for extra output.")
    parser.add_argument("-E", "--execJob", action='store_true', default=False, help="may take long time, test before")


def main(args):
    job_id = int(args.id)

    # 1) instantiate operator (creates its own AQDrop client)
    operator = AqdropOperator(args.verb, args.execJob)

    # 2) pull queued job from DB
    operator.pull_job_input(job_id)

    # 3) disassemble 'input' record into circuits + metadata
    circL, inputMD = operator.parse_job_input()

    # 4) connect to QPU (uses queue name from the job + QUBIC_CALIB_BASE_PATH)
    operator.qpu_connect()

    # 5) run all circuits on the QPU
    operator.qpu_run_job()

    if not args.execJob:
        output = {
            "shots": operator.shots,
            "num_qubits": operator.num_qubits,
            "num_2q_gates": operator.num_2q_gates,
            "exec_time": operator.exec_time,
        }
        _print_execution_table(circL, inputMD, output)
        print(f'\njobs NOT executed, only dry execution on {operator.job["queue_name"]}, use -E for running on QPU\n')
        return

    # 6) assemble QPU output (counts, shots, exec_time, circ_transp_qpy)
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
