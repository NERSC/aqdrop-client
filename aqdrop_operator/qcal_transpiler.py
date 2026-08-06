"""Delay-aware conversion from native Qiskit circuits to qcal circuits.

qcal's stock ``QiskitTranspiler`` only passes qubits to its gate mapper.  It
therefore cannot preserve a Qiskit delay duration, and QPY additionally
changes explicit time units to ``dt``.  This converter passes the complete
operation and the job's declared delay unit to each gate constructor.
"""

import qiskit

from qcal.circuit import Barrier, Circuit, CircuitSet, Layer
from qcal.gate.single_qubit import Idle, Meas, Rz, X, X90
from qcal.gate.two_qubit import CZ
from qcal.interface.superstaq.transpiler import QiskitTranspiler
from qcal.transpilation.utils import GateMapper


_UNIT_TO_SECONDS = {
    "s": 1.0,
    "ms": 1e-3,
    "us": 1e-6,
    "ns": 1e-9,
    "ps": 1e-12,
}


class UnsupportedGate(Exception):
    """A Qiskit operation cannot be represented by this QPU."""


class StrictGateMapper(GateMapper):
    """Report unsupported operations by name instead of a bare exception."""

    def __missing__(self, key):
        def raise_unsupported(*args, **kwargs):
            raise UnsupportedGate(
                f"{key!r} has no qcal equivalent on this chip "
                f"(known: {sorted(self)})"
            )

        return raise_unsupported


def _delay_to_seconds(operation, declared_unit):
    unit = operation.unit
    if unit == "dt":
        unit = declared_unit
    if unit not in _UNIT_TO_SECONDS:
        raise UnsupportedGate(f"delay has unusable unit {unit!r}")
    return float(operation.duration) * _UNIT_TO_SECONDS[unit]


_DEFAULT_GATES = {
    "rz": lambda qubits, operation, context: Rz(
        qubits, float(operation.params[0])
    ),
    "sx": lambda qubits, operation, context: X90(qubits),
    "x": lambda qubits, operation, context: X(qubits),
    "cz": lambda qubits, operation, context: CZ(qubits),
    "delay": lambda qubits, operation, context: Idle(
        qubits,
        duration=_delay_to_seconds(operation, context["delay_unit"]),
    ),
    "measure": lambda qubits, operation, context: Meas(qubits),
}


class GenericQiskitTranspiler(QiskitTranspiler):
    """Convert native-basis Qiskit circuits without losing timing data."""

    def __init__(self, *, delay_unit):
        super().__init__(gate_mapper=StrictGateMapper(dict(_DEFAULT_GATES)))
        if delay_unit not in _UNIT_TO_SECONDS:
            raise ValueError(f"unsupported declared delay unit {delay_unit!r}")
        self._delay_unit = delay_unit

    def transpile(self, circuits):
        if isinstance(circuits, qiskit.QuantumCircuit):
            circuits = [circuits]
        return CircuitSet(circuits=[self._convert(circuit) for circuit in circuits])

    def _convert(self, circuit):
        context = {"delay_unit": self._delay_unit}
        qcal_circuit = Circuit()
        layer = Layer()

        def flush():
            nonlocal layer
            if layer.n_gates > 0:
                qcal_circuit.append(layer)
            layer = Layer()

        for instruction in circuit.data:
            operation = instruction.operation
            qubits = tuple(
                circuit.find_bit(qubit).index for qubit in instruction.qubits
            )

            if operation.name == "barrier":
                flush()
                qcal_circuit.append(Barrier(qubits))
                continue

            if any(qubit in layer.qubits for qubit in qubits):
                flush()
            layer.append(
                self._gate_mapper[operation.name](qubits, operation, context)
            )

        flush()
        return qcal_circuit
