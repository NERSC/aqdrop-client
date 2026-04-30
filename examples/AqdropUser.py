"""User-side pipeline class for submitting/retrieving AQDrop jobs.

Submission pipeline:
    assemble_job_input(circL, inpMD)  ->  push_job_input()

Retrieval pipeline:
    pull_job(job_id)                  ->  parse_job()
"""

import base64
import io
from pprint import pprint

import aqdrop
import httpx
from qiskit import QuantumCircuit, qpy


def _submit_error_user_message(exc: BaseException) -> str:
    """Best-effort API error text (works with httpx.HTTPStatusError or aqdrop.AqdropHttpError)."""
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            data = exc.response.json()
        except Exception:
            text = (exc.response.text or "").strip()
            return text[:2000] if text else str(exc)
        if isinstance(data, dict) and "detail" in data:
            d = data["detail"]
            if isinstance(d, str):
                return d
            if isinstance(d, list):
                return "; ".join(str(x.get("msg", x)) if isinstance(x, dict) else str(x) for x in d)
            return str(d)
        return str(data) if data is not None else str(exc)
    return str(exc)


def print_circuit_table(circuits, meta: dict):
    """Pretty-print circuit list with their requested shots.

    Standalone helper so a dry-run preview can call it without instantiating
    AqdropUser (and therefore without opening a network connection).
    """
    shots = meta.get("shots", [])
    if isinstance(shots, int):
        shots = [shots] * len(circuits)
    print("idx  num_qubits  num_shots")
    for idx, qc in enumerate(circuits):
        num_shots = shots[idx] if idx < len(shots) else "n/a"
        print(f"{idx:>3}  {qc.num_qubits:>10}  {num_shots}")


class AqdropUser:
    def __init__(self, verb: int = 1):
        self.verb = verb
        self.client = aqdrop.AqdropClient()

        # State filled in by the pipeline steps below.
        self.job_id = None
        self.job = None
        self.circL = None
        self.inputMD = None
        self.job_input = None
        self.output = None
        self.transpiledL = None


    def assemble_job_input(self, circL, inpMD: dict) -> dict:
        circuits = [circL] if isinstance(circL, QuantumCircuit) else list(circL)
        assert "queue_name" in inpMD
        assert "pref_qubits" in inpMD

        meta = dict(inpMD)
        shots = meta.get("shots")
        if isinstance(shots, int):
            shots = [shots] * len(circuits)
        assert isinstance(shots, list) and len(shots) == len(circuits)
        meta["shots"] = shots
        meta.setdefault("comment", None)
        meta["num_qubits"] = [qc.num_qubits for qc in circuits]

        buffer = io.BytesIO()
        qpy.dump(circuits, buffer)
        qpy_blob = base64.b64encode(buffer.getvalue()).decode()

        self.circL = circuits
        self.inputMD = meta
        self.job_input = {"circ_inp_qpy": qpy_blob, **meta}

        print(f"assembled job_input for {len(circuits)} circuits, queue={meta['queue_name']}")
        print_circuit_table(circuits, meta)
        return self.job_input


    def push_job_input(self) -> int:
        assert self.job_input is not None
        queue = self.job_input["queue_name"]
        submit_errors = (httpx.HTTPStatusError,)
        aqdrop_http = getattr(aqdrop, "AqdropHttpError", None)
        if aqdrop_http is not None:
            submit_errors = (httpx.HTTPStatusError, aqdrop_http)
        try:
            submitted = self.client.submit_job(queue, self.job_input)
        except submit_errors as exc:
            print("AQDrop API rejected job submission (job was not queued).")
            print(_submit_error_user_message(exc))
            raise SystemExit(1) from None
        self.job_id = submitted["id"]
        print(f"pushed job_input; assigned job_id={self.job_id}")
        print(f"   ./job_retrieve.py --id {self.job_id}")
        return self.job_id


    def pull_job(self, job_id: int) -> dict:
        job = self.client.get_job(job_id)
        self.job_id = job_id
        self.job = job
        summary = {k: job.get(k) for k in ("id", "owner_name", "queue_name", "status")}
        print(f"pulled job: {summary}")
        return job


    def parse_job(self):
        """Unpack 'input' (always present) and 'output' (if available).

        Returns (circL, inputMD, output, transpiledL); output and transpiledL
        are None when the job has no result yet.
        """
        assert self.job is not None
        job_input = self.job["input"]
        self.circL = self.client.extract_qiskit(job_input["circ_inp_qpy"])
        self.inputMD = {k: v for k, v in job_input.items() if k != "circ_inp_qpy"}

        output = self.job.get("output")
        if output is None:
            self.output = None
            self.transpiledL = None
            print(f'parsed job: {len(self.circL)} input circuits, no output yet (status={self.job["status"]})')
            return self.circL, self.inputMD, None, None

        self.transpiledL = (
            self.client.extract_qiskit(output["circ_transp_qpy"]) if "circ_transp_qpy" in output else None
        )
        self.output = {k: v for k, v in output.items() if k != "circ_transp_qpy"}
        n_t = len(self.transpiledL) if self.transpiledL else 0
        print(f'parsed job: {len(self.circL)} input circuits, output present, {n_t} transpiled circuits')
        return self.circL, self.inputMD, self.output, self.transpiledL


    def print_shot_summary(self):
        assert self.inputMD is not None and self.output is not None
        asked = self.inputMD["shots"]
        received = self.output["shots"]
        print(f"shots asked={asked}")
        print(f"received={received}")
        if asked != received:
            missing = [a - r for a, r in zip(asked, received)]
            print(f"missing={missing}")


    def print_output_counts(self):
        assert self.output is not None
        assert self.inputMD is not None
        counts_list = self.output["counts"]
        asked_list = self.inputMD["shots"]
        received_list = self.output["shots"]
        print(f"Output counts for {len(counts_list)} circuit(s)")
        for idx, counts in enumerate(counts_list):
            a = asked_list[idx]
            r = received_list[idx]
            print(f"circuit[{idx}] shots asked={a} received={r}")
            pprint(counts)
