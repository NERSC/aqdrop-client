"""Shared AQDrop helpers for submitting and retrieving example Qiskit jobs."""

import base64
import io
from pprint import pprint

import aqdrop
import httpx
from qiskit import QuantumCircuit
from qiskit import qpy


def as_circuit_list(circ) -> list[QuantumCircuit]:
    if isinstance(circ, QuantumCircuit):
        return [circ]
    return list(circ)


def encode_qpy_circuit(circ) -> str:
    circuits = as_circuit_list(circ)
    buffer = io.BytesIO()
    qpy.dump(circuits, buffer)
    return base64.b64encode(buffer.getvalue()).decode()


def extract_qiskit_circuits(job: dict):
    shots = job.get("input", {}).get("shots", 0)
    if isinstance(shots, list):
        total_shots = sum(shots)
    elif isinstance(shots, int):
        total_shots = shots
    else:
        total_shots = 0

    qpy_blob = job.get("input", {}).get("qpy")
    if qpy_blob is None:
        print(f"Packed circuits: 0, total requested shots: {total_shots}")
        return []

    import qiskit
    import qiskit.qpy

    embedded_qpy = base64.b64decode(qpy_blob)
    circuits = qiskit.qpy.load(io.BytesIO(embedded_qpy))

    if not isinstance(circuits, list):
        circuits = [circuits]

    print(f"Packed circuits: {len(circuits)}, total requested shots: {total_shots}")
    return circuits


def print_circuit_table(circ, meta: dict):
    circuits = as_circuit_list(circ)
    shots = meta.get("shots", [])
    if isinstance(shots, int):
        shots = [shots] * len(circuits)

    print("idx  num_qubits  num_shots")
    for idx, qc in enumerate(circuits):
        num_shots = shots[idx] if idx < len(shots) else "n/a"
        print(f"{idx:>3}  {qc.num_qubits:>10}  {num_shots}")


def submit_job(queue: str, circ, meta: dict, *, client: aqdrop.AqdropClient, verb: int = 1) -> int:
    circuits = as_circuit_list(circ)
    meta = dict(meta)
    if "queue_name" in meta:
        raise ValueError("queue_name must be passed as the queue argument, not in meta")
    shots = meta.get("shots")
    if isinstance(shots, list):
        assert len(circuits) == len(shots), "circ and shots must have the same length"
    meta.setdefault("comment", None)
    meta["num_qubits"] = [qc.num_qubits for qc in circuits]
    meta["queue_name"] = queue
    job_input = {"qpy": encode_qpy_circuit(circuits)}
    job_input.update(meta)

    if verb > 2:
        pprint(job_input)

    if client is None:
        raise ValueError("client is required")

    try:
        submitted = client.submit_job(queue, job_input)
    except httpx.HTTPStatusError as e:
        print("Job submission failed.")
        resp = e.response
        detail = resp.json().get("detail") if "application/json" in resp.headers.get("content-type", "") else resp.text
        print(f"Error {resp.status_code}: {detail}.")
        return 0
    except httpx.ConnectError as e:
        print("Could not connect to AQDROP service. Is AQDROP_HOSTNAME properly set?")
        print(f"Error: {e}")
        return 0

    job_id = submitted["id"]
    print(f"Job submission successful; assigned job ID {job_id}.")
    print(f"Submitted {len(circuits)} circuits to queue={meta['queue_name']}")
    print_circuit_table(circuits, meta)
    print(f"   ./job_retrieve.py --id {job_id}")
    if verb > 1:
        pprint(submitted)
    return job_id
