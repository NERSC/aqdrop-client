"""High-level stateful session manager for submitting/retrieving AQDrop jobs.

Submission pipeline:
    assemble_job_input(circL, inpMD)  ->  push_job_input()

Retrieval pipeline:
    pull_job(job_id)                  ->  parse_job()
"""

import httpx
from qiskit import QuantumCircuit

from .main import AqdropClient
from . import cli_utils

class AqdropUser:
    def __init__(self, verb: int = 1):
        self.verb = verb
        self.client = AqdropClient()

        # State filled in by the pipeline steps below.
        self.job_id = None
        self.job = None
        self.circL = None
        self.inputMD = None
        self.job_input = None
        self.output = None
        self.transpiledL = None

    def assemble_job_input(self, circL, inpMD: dict) -> dict:
        self.job_input, self.circL, self.inputMD = self.client.assemble_job_input(circL, inpMD)

        if self.verb > 0:
            print(f"assembled job_input for {len(self.circL)} circuits, queue={self.inputMD['queue_name']}")
            cli_utils.print_circuit_table(self.circL, self.inputMD)

        return self.job_input

    def push_job_input(self) -> int:
        assert self.job_input is not None
        queue = self.job_input["queue_name"]

        # Define errors to catch
        submit_errors = (httpx.HTTPStatusError,)
        aqdrop_http = getattr(self.client, "AqdropHttpError", None) # Adjusted to check client or package
        if aqdrop_http is not None:
            submit_errors = (httpx.HTTPStatusError, aqdrop_http)

        try:
            submitted = self.client.submit_job(queue, self.job_input)
        except submit_errors as exc:
            print("AQDrop API rejected job submission (job was not queued).")
            print(cli_utils.get_submit_error_message(exc))
            raise SystemExit(1) from None

        self.job_id = submitted["id"]
        if self.verb > 0:
            print(f"pushed job_input; assigned job_id={self.job_id}")
            print(f"   ./job_retrieve.py --id {self.job_id}")

        return self.job_id

    def pull_job(self, job_id: int) -> dict:
        job = self.client.get_job(job_id)
        self.job_id = job_id
        self.job = job

        if self.verb > 0:
            summary = {k: job.get(k) for k in ("id", "owner_name", "queue_name", "status")}
            print(f"pulled job: {summary}")

        return job

    def parse_job(self):
        """Unpack 'input' (always present) and 'output' (if available).

        Returns (circL, inputMD, output, transpiledL); output and transpiledL
        are None when the job has no result yet.
        """
        assert self.job is not None

        res = self.client.parse_job(self.job)
        self.circL, self.inputMD, self.output, self.transpiledL = res

        if self.verb > 0:
            if self.output is None:
                print(f'parsed job: {len(self.circL)} input circuits, no output yet (status={self.job["status"]})')
            else:
                n_t = len(self.transpiledL) if self.transpiledL else 0
                print(f'parsed job: {len(self.circL)} input circuits, output present, {n_t} transpiled circuits')

        return res

    def print_shot_summary(self):
        assert self.inputMD is not None and self.output is not None
        cli_utils.print_shot_summary(self.inputMD, self.output)

    def print_output_counts(self):
        assert self.output is not None
        assert self.inputMD is not None
        cli_utils.print_output_counts(self.inputMD, self.output)
