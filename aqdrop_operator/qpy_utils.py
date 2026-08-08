"""Encode and decode Qiskit circuits carried in AQDrop job payloads."""

from __future__ import annotations

import base64
import binascii
import io
from collections.abc import Sequence


def decode_circuits(payload: str):
    """Decode a base64 QPY payload into a list of circuits."""
    try:
        raw_payload = base64.b64decode(payload, validate=True)
    except (binascii.Error, TypeError, ValueError) as exc:
        raise ValueError("circ_inp_qpy is not a valid base64 QPY payload") from exc

    from qiskit import qpy

    circuits = qpy.load(io.BytesIO(raw_payload))
    return list(circuits)


def encode_circuits(circuits: Sequence) -> str:
    """Encode circuits as a base64 QPY payload for an AQDrop job result."""
    from qiskit import qpy

    output = io.BytesIO()
    qpy.dump(list(circuits), output)
    return base64.b64encode(output.getvalue()).decode("ascii")
