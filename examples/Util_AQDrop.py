"""Shared AQDrop helpers for submitting and retrieving example Qiskit jobs."""

import base64
import io
import json
from numbers import Number
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


def extract_transpiled_qiskit_circuits(job: dict, client: aqdrop.AqdropClient):
    output = _decode_json_string(job.get("output"))
    if not isinstance(output, dict):
        print("Transpiled circuits: 0")
        return []

    qpy_blob = output.get("transpiled_qpy")
    if qpy_blob is None:
        print("Transpiled circuits: 0")
        return []

    circuits = client.extract_qiskit(qpy_blob)
    print(f"Transpiled circuits: {len(circuits)}")
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


def _decode_json_string(value):
    if not isinstance(value, str):
        return value

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _is_count_value(value) -> bool:
    return isinstance(value, Number) and not isinstance(value, bool)


def _normalize_count_map(value, *, allow_empty: bool = False):
    value = _decode_json_string(value)
    if not isinstance(value, dict):
        return None
    if not value:
        return {} if allow_empty else None
    if all(isinstance(key, (str, int)) and _is_count_value(count) for key, count in value.items()):
        return dict(value)
    return None


def _sorted_count_items(value: dict):
    def sort_key(item):
        key = item[0]
        if isinstance(key, int):
            return (0, key)
        if isinstance(key, str) and key.isdigit():
            return (0, int(key))
        return (1, str(key))

    return sorted(value.items(), key=sort_key)


def _extract_count_groups(value) -> list[dict]:
    value = _decode_json_string(value)
    count_map = _normalize_count_map(value, allow_empty=True)
    if count_map is not None:
        return [count_map]

    groups = []
    if isinstance(value, list):
        for item in value:
            count_map = _normalize_count_map(item, allow_empty=True)
            if count_map is not None:
                groups.append(count_map)
        return groups

    if isinstance(value, dict):
        for _, item in _sorted_count_items(value):
            count_map = _normalize_count_map(item, allow_empty=True)
            if count_map is not None:
                groups.append(count_map)
        return groups

    return groups


def extract_output_counts(output) -> list[dict]:
    output = _decode_json_string(output)
    direct_counts = _normalize_count_map(output)
    if direct_counts is not None:
        return [direct_counts]

    if isinstance(output, dict) and "counts" in output:
        return _extract_count_groups(output["counts"])

    if not isinstance(output, (dict, list)):
        return []

    count_groups = []

    direct_groups = []
    if isinstance(output, list):
        direct_groups = _extract_count_groups(output)
    elif isinstance(output, dict) and "counts" not in output:
        direct_groups = _extract_count_groups(output)
        if len(direct_groups) != len(output):
            direct_groups = []
    if direct_groups:
        return direct_groups

    def collect(value):
        value = _decode_json_string(value)
        if isinstance(value, dict):
            if "counts" in value:
                count_groups.extend(_extract_count_groups(value["counts"]))
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(output)
    return count_groups


def requested_shots(job: dict, num_counts: int = 0) -> list:
    shots = job.get("input", {}).get("shots", [])
    if isinstance(shots, list):
        return shots
    if isinstance(shots, int):
        repeat = num_counts if num_counts > 1 else 1
        return [shots] * repeat
    return []


def received_shots(output) -> list:
    count_groups = extract_output_counts(output)
    return [sum(counts.values()) for counts in count_groups]


def print_shot_summary(job: dict):
    received = received_shots(job.get("output"))
    asked = requested_shots(job, len(received))

    print(f"shots asked={asked}")
    print(f"received={received}")
    if asked != received:
        missing = []
        max_len = max(len(asked), len(received))
        for idx in range(max_len):
            asked_val = asked[idx] if idx < len(asked) else 0
            received_val = received[idx] if idx < len(received) else 0
            missing.append(asked_val - received_val)
        print(f"missing={missing}")


def print_output_counts(output):
    count_groups = extract_output_counts(output)
    if not count_groups:
        print("No counts found in output.")
        return

    print(f"Output counts for {len(count_groups)} circuit(s)")
    for idx, counts in enumerate(count_groups):
        print(f"circuit[{idx}]")
        pprint(counts)


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
