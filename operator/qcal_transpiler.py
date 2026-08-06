"""Generic Qiskit -> qcal transpiler for the AQDrop operator.

One class that converts ANY Qiskit circuit into a qcal circuit, so the
operator needs no experiment-specific code: Bell, T1, T2, echo/DD, CZ
characterization and RPE all go through the same path.

    from qcal_transpiler import GenericQiskitTranspiler

    transpiler = GenericQiskitTranspiler(
        basis_gates=["rz", "sx", "x"],      # chip's native set (from profile)
        qubit_map={0: 20},                  # virtual -> physical
        delay_unit="ns",                    # from job["input"]["delay_unit"]
    )
    qcal_circuits = transpiler.transpile(qiskit_circuits).circuits

WHY THIS SUBCLASSES qcal's QiskitTranspiler
-------------------------------------------
qcal's QiskitTranspiler (qcal/interface/superstaq/transpiler.py) is correct
for plain gate-model circuits in an 'rz' basis -- the AQDrop team's
orignal_test_qpu.py Bell test runs fine through it, and angles are exact.
Subclassing keeps that lineage: this class satisfies qcal's Transpiler
interface, so it can be passed directly as QPU(transpiler=...) and slots into
qcal's own run pipeline (qcal/qpu/qpu.py calls transpiler.transpile()).

What the parent cannot do -- each verified, and each needed for calibration-
class circuits:

1. Timed delays.  The parent calls gate_mapper[name](qubits), so mapping
   'delay' to Idle constructs Idle(qubits) with the DEFAULT duration=0.0 --
   a 409.6 us idle silently becomes 0 s, no error.  T1/T2/RPE all die
   silently.  Here 'delay' becomes Idle(q, duration=<seconds>).

2. Partial barriers.  The parent's walker OVERWRITES the layer under
   construction when it hits a barrier, instead of flushing it: in
   x(0); barrier(1); x(1) the x(0) is silently dropped.  Latent for
   single-qubit or full-width-barrier circuits; real for anything else.
   (Worth reporting upstream to qcal.)

3. Parametrized gates other than literal 'rz'.  The parent forwards a
   parameter only when the gate is named 'rz'.  AQDrop's current basis
   ['p','sx','cz'] with {'p': Z} therefore drops every angle.  A Bell
   circuit is provably insensitive to that substitution (identical 00/11
   counts -- which is why orignal_test_qpu.py's Bell test cannot catch it),
   but AQDrop's own random-angle example circ_tens2(0.8, -2.5) collapses
   from a {.08/.76/.02/.14} spread to 100% |00>.  Fix: basis 'rz' + Rz,
   which is this class's default.

4. Virtual -> physical qubit mapping.  The parent uses circuit indices as
   physical labels, so a 1-qubit calibration circuit must be transpiled
   against the full coupling map just to land on the right qubit.  Here a
   qubit_map ({0: 20}) does it directly.

THE QPY DELAY-UNIT CONTRACT
---------------------------
AQDrop ships circuits through the database as QPY blobs.  On Qiskit 2.3.1
QPY does not preserve the delay unit: delay(800, unit="ns") arrives as
unit='dt' with the number intact (and float durations in seconds make
qpy.load raise outright).  The AQDrop job contract therefore carries
job["input"]["delay_unit"], and this transpiler re-attaches it whenever a
delay arrives as 'dt'.  Users should always create delays in integer ns.
"""

import qiskit

from qcal.circuit import Barrier, Circuit, CircuitSet, Layer
from qcal.gate.single_qubit import Idle, Meas, Rz, X, X90
from qcal.gate.two_qubit import CZ
from qcal.interface.superstaq.transpiler import QiskitTranspiler
from qcal.transpilation.utils import GateMapper


_UNIT_TO_SECONDS = {"s": 1.0, "ms": 1e-3, "us": 1e-6, "ns": 1e-9, "ps": 1e-12}


class UnsupportedGate(Exception):
    """Circuit contains something this chip cannot express.

    Typed so the operator can turn it into dispatch_job(FAILED, {"reason":
    ...}) and keep the daemon alive.  It must never become SystemExit: an
    unsupported gate is routine user input once arbitrary circuits are
    allowed, and today it kills the AQDrop daemon and strands the job in
    QUEUED.
    """


class StrictGateMapper(GateMapper):
    """GateMapper that raises a typed, named error for unknown gates.

    qcal's GateMapper.__missing__ returns a callable raising a bare
    Exception; this one raises UnsupportedGate and lists what IS supported,
    so the message that reaches the user's job output is actionable.
    """

    def __missing__(self, key):
        def _raise(*args, **kwargs):
            raise UnsupportedGate(
                f"{key!r} has no qcal equivalent on this chip "
                f"(known: {sorted(self)})"
            )
        return _raise


def _delay_to_seconds(operation, declared_unit):
    """Convert a Qiskit delay to seconds, repairing the QPY 'dt' loss."""
    unit = operation.unit
    if unit == "dt":
        # QPY degraded the unit; trust what the job declared.
        unit = declared_unit
    if unit not in _UNIT_TO_SECONDS:
        raise UnsupportedGate(f"delay has unusable unit {unit!r}")
    return float(operation.duration) * _UNIT_TO_SECONDS[unit]


# Default gate table.  Every entry takes (qubits, operation, ctx) where ctx
# is a dict carrying conversion context (currently just 'delay_unit').
# Adding a gate is one line -- there is no experiment-specific branch.
_DEFAULT_GATES = {
    "rz":      lambda q, op, ctx: Rz(q, float(op.params[0])),
    "sx":      lambda q, op, ctx: X90(q),
    "x":       lambda q, op, ctx: X(q),
    "cz":      lambda q, op, ctx: CZ(q),
    "delay":   lambda q, op, ctx: Idle(
                   q, duration=_delay_to_seconds(op, ctx["delay_unit"])),
    "measure": lambda q, op, ctx: Meas(q),
}


class GenericQiskitTranspiler(QiskitTranspiler):
    """Qiskit -> qcal transpiler for arbitrary circuits.

    Args:
        gate_mapper: full replacement gate table ({name: fn(qubits, op, ctx)}).
            Default None uses the built-in rz/sx/x/cz/delay/measure table.
        extra_gates: dict merged ON TOP of the default table -- the easy way
            to add one chip-specific gate without restating the rest.
        qubit_map: virtual index -> physical qubit, e.g. {0: 20}.  Default
            None means identity (circuit indices ARE physical labels, as in
            the routed/initial_layout flow).  Overridable per transpile()
            call.
        delay_unit: unit assumed for delays that arrive as 'dt' (see module
            docstring).  Defaults to 'ns', the AQDrop contract value.
        basis_gates / coupling_map / optimization_level: if basis_gates is
            given, each circuit is first run through qiskit.transpile() with
            these settings, so callers can hand raw circuits (h/cx Bell) and
            get qcal out in one step.  Default None skips this -- the AQDrop
            operator does its own transpile where routing decisions live.
            The pre-transpiled circuits are kept as .last_native for
            circ_transp_qpy / stats.
    """

    def __init__(self,
                 gate_mapper=None,
                 extra_gates=None,
                 qubit_map=None,
                 delay_unit="ns",
                 basis_gates=None,
                 coupling_map=None,
                 optimization_level=0):
        if gate_mapper is None:
            gate_mapper = dict(_DEFAULT_GATES)
        if extra_gates:
            gate_mapper = {**gate_mapper, **extra_gates}
        # Parent stores this as _gate_mapper (property: .gate_mapper).
        super().__init__(gate_mapper=StrictGateMapper(gate_mapper))

        self._qubit_map = qubit_map
        self._delay_unit = delay_unit
        self._basis_gates = basis_gates
        self._coupling_map = coupling_map
        self._optimization_level = optimization_level
        self.last_native = []   # qiskit circuits actually converted, per run

    def transpile(self, circuits, qubit_map=None) -> CircuitSet:
        """Transpile Qiskit circuit(s) to a qcal CircuitSet.

        Args:
            circuits: one Qiskit circuit or a list of them.
            qubit_map: per-call override of the constructor's qubit_map.

        Returns:
            CircuitSet, index-aligned with the input list (the alignment the
            AQDrop user relies on to match counts back to circuits).
        """
        if isinstance(circuits, qiskit.QuantumCircuit):
            circuits = [circuits]
        if qubit_map is None:
            qubit_map = self._qubit_map

        native = []
        for circuit in circuits:
            if self._basis_gates is not None:
                circuit = qiskit.transpile(
                    circuit,
                    basis_gates=self._basis_gates,
                    coupling_map=self._coupling_map,
                    optimization_level=self._optimization_level,
                )
            native.append(circuit)
        self.last_native = native

        tcircuits = [
            self._convert(circuit, qubit_map) for circuit in native
        ]
        return CircuitSet(circuits=tcircuits)

    def _convert(self, circuit, qubit_map) -> Circuit:
        """Walk one native-basis Qiskit circuit into a qcal Circuit.

        Gates sharing no qubits are packed into one Layer so they run in
        parallel; a repeated qubit flushes the layer, and a barrier flushes
        then appends (never overwrites -- the parent's walker drops pending
        gates on partial barriers).
        """
        ctx = {"delay_unit": self._delay_unit}
        qcal_circuit = Circuit()
        layer = Layer()

        def flush():
            nonlocal layer
            if layer.n_gates > 0:
                qcal_circuit.append(layer)
            layer = Layer()

        for instruction in circuit.data:
            operation = instruction.operation
            name = operation.name
            qubits = tuple(
                self._map_qubit(circuit.find_bit(q).index, qubit_map)
                for q in instruction.qubits
            )

            if name == "barrier":
                flush()
                qcal_circuit.append(Barrier(qubits))
                continue

            if any(q in layer.qubits for q in qubits):
                flush()
            layer.append(self._gate_mapper[name](qubits, operation, ctx))

        flush()
        return qcal_circuit

    @staticmethod
    def _map_qubit(index, qubit_map):
        if qubit_map is None:
            return index
        try:
            return qubit_map[index]
        except KeyError:
            raise UnsupportedGate(
                f"circuit uses qubit index {index} but qubit_map only "
                f"covers {sorted(qubit_map)}"
            ) from None
