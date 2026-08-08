#!/usr/bin/env python3

"""Run a selected circuit directly on one Qubic QPU and print counts.

Run one of the four implemented circuits:

    python run_local_zoo.py --task bell
    python run_local_zoo.py --task bell3
    python run_local_zoo.py --task oneq1
    python run_local_zoo.py --task oneq2

Circuit definitions:

* ``bell``: two qubits with H(0), CX(0, 1), and both qubits measured.
* ``bell3``: the ``bell`` circuit plus an idle third qubit that is measured.
* ``oneq1``: one qubit with X(0), followed by measurement.
* ``oneq2``: two qubits with X(0) and H(1), followed by measurement.

Use ``-q`` to select physical qubits, for example:

    python run_local_zoo.py --task bell -q 1 2

Use ``--qasm NAME`` and/or ``--qpy NAME`` to save the transpiled circuit
under ``out/``.


Example job for IQM
./run_local_zoo.py --task oneq1  --qpu IQM  --pref_qubits 20

Example job on X6Y3
./run_local_zoo.py --task oneq1  --qpu X6Y3  --pref_qubits 1
"""

import argparse
import os
from pathlib import Path

import qcal
import qcal.settings as settings
import qiskit
import yaml
from qcal.backend.qubic.qpu import QubicQPU
from qcal.circuit import Barrier
from qcal.gate.single_qubit import Meas, X90, Z
from qcal.gate.two_qubit import CZ
from qcal.interface.superstaq.transpiler import QiskitTranspiler
from qcal.utils import load_from_pickle
from qiskit import QuantumCircuit, qasm2, qpy
from qiskit.transpiler.exceptions import TranspilerError

from config_utils import get_qubit_pairs


GATE_MAPPER = {
    "barrier": Barrier,
    "measure": Meas,
    "cz": CZ,
    "sx": X90,
    "p": Z,
}

TASKS = ("bell", "bell3", "oneq1", "oneq2")


def build_circuit(task: str) -> QuantumCircuit:
    """Build the circuit selected by ``task``."""
    assert task in TASKS, f"unsupported task={task!r}; expected one of {TASKS}"

    if task == "bell":
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.cx(0, 1)
    elif task == "bell3":
        qc = QuantumCircuit(3, 3)
        qc.h(0)
        qc.cx(0, 1)
    elif task == "oneq1":
        qc = QuantumCircuit(1, 1)
        qc.x(0)
    else:
        qc = QuantumCircuit(2, 2)
        qc.x(0)
        qc.h(1)

    qc.measure(range(qc.num_qubits), range(qc.num_clbits))
    return qc


def extract_physical_layout(qc):
    """Extracts physical IDs."""
    assert qc.layout is not None, "transpiled circuit has no layout"
    physical_layout = qc.layout.final_index_layout(filter_ancillas=True)
    assert physical_layout, "transpiled circuit has no physical qubit layout"
    assert all(isinstance(qubit, int) and qubit >= 0 for qubit in physical_layout)
    assert len(set(physical_layout)) == len(physical_layout), (
        "physical qubit layout contains duplicates"
    )
    return physical_layout


def qiskit_transpile(
    qc,
    basis_gates,
    coupling_map,
    initial_layout,
):
    """Run Qiskit transpile for QPU basis and layout; print and exit on TranspilerError."""
    try:
        return qiskit.transpile(
            qc,
            basis_gates=basis_gates,
            coupling_map=coupling_map,
            initial_layout=initial_layout,
        )
    except TranspilerError as exc:
        msg = str(exc).strip()
        if msg:
            last_line = msg.split("\n")[-1].strip()
        else:
            last_line = repr(exc)
        print("qiskit.transpile failed:", last_line)
        raise SystemExit(1)


def add_args(parser: argparse.ArgumentParser):
    p = parser.add_argument
    p("--qpu", default="X6Y3", help="QPU queue/chip name.")
    p(
        "--calibBase",
        default="/dataVault2026/qpus_calib",
        help="active_qpus.yaml + calibration folder.",
    )
    p("-n", "--shots", type=int, default=2000, help="Requested shots.")
    p("--task", choices=TASKS, default="bell", help="Circuit to run.")
    p(
        "-q",
        "--pref_qubits",
        type=int,
        nargs="+",
        default=None,
        metavar="QUBIT",
        help="Physical qubits list for transpiler.",
    )
    p("--qasm", default=None, metavar="NAME", help="Save transpiled QASM to out/NAME.qasm.")
    p("--qpy", default=None, metavar="NAME", help="Save transpiled circuit to out/NAME.qpy.")


def load_qpu_config(qpu_name: str, calib_base: str):
    assert os.path.isdir(calib_base), f"missing calibration base path={calib_base}"

    active_qpus_path = os.path.join(calib_base, "active_qpus.yaml")
    assert os.path.isfile(active_qpus_path), f"missing active QPU configuration={active_qpus_path}"
    with open(active_qpus_path, encoding="utf-8") as fd:
        qubic_calib = yaml.safe_load(fd)

    assert isinstance(qubic_calib, dict), f"invalid QPU configuration={active_qpus_path}"
    assert qpu_name in qubic_calib, f"qpu {qpu_name} not in {active_qpus_path}"
    chip_config = qubic_calib[qpu_name]
    assert all(key in chip_config for key in ("calib_tag", "ip", "port"))

    calib_ver = f"{qpu_name}_{chip_config['calib_tag']}"
    settings_config_path = os.path.join(calib_base, calib_ver)
    assert os.path.isdir(settings_config_path), f"missing calibration path={settings_config_path}"

    qpu_ip = chip_config["ip"]
    qpu_port = int(chip_config["port"])
    assert qpu_ip, f"missing IP address for qpu={qpu_name}"
    assert 0 < qpu_port < 65536, f"invalid port={qpu_port} for qpu={qpu_name}"
    return settings_config_path, qpu_ip, qpu_port


def output_path(name: str, suffix: str) -> Path:
    """Return a safe output path below the local out directory."""
    assert name, "output name must not be empty"
    assert Path(name).name == name, "output name must not contain a directory"
    out_dir = Path("out")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{name}.{suffix}"


def main(args):
    assert args.shots > 0, f"shots must be positive, got {args.shots}"

    qc = build_circuit(args.task)
    pref_qubits = args.pref_qubits
    if pref_qubits is not None:
        assert qc.num_qubits == len(pref_qubits), (
            f"task={args.task} uses {qc.num_qubits} qubits, "
            f"but pref_qubits={pref_qubits}"
        )
        assert all(qubit >= 0 for qubit in pref_qubits), "physical qubits must be non-negative"
        assert len(set(pref_qubits)) == len(pref_qubits), "physical qubits must be unique"

    settings_config_path, qpu_ip, qpu_port = load_qpu_config(args.qpu, args.calibBase)
    print(f"resolved qpu={args.qpu}, ip={qpu_ip}, port={qpu_port}")
    settings.Settings.config_path = settings_config_path + os.sep

    classifier = load_from_pickle(settings_config_path + "/ClassificationManager.pkl")

    qcal_cfg = qcal.Config()
    qpu = QubicQPU(qcal_cfg, classifier=classifier, ip_address=qpu_ip, port=qpu_port)

    qubit_pairs = get_qubit_pairs(f"{settings_config_path}/config.yaml")

    basis_gates = ["p", "sx", "cz"]
    print("basis_gates", basis_gates)
    print("qubit_pairs", qubit_pairs)
    print("pref_qubits", pref_qubits)

    print("input circuit:")
    print(qc)

    qcT = qiskit_transpile(
        qc,
        basis_gates=basis_gates,
        coupling_map=qubit_pairs,
        initial_layout=pref_qubits,
    )

    phys_qubits = extract_physical_layout(qcT)
    print(f"transpiled circuit to gates={basis_gates}, phys qubits={phys_qubits}")
    print(qcT)
    if args.qasm is not None:
        qasm_str = qasm2.dumps(qcT)
        out_file = output_path(args.qasm, "qasm")
        with out_file.open("w", encoding="utf-8") as fd:
            fd.write(qasm_str)
        print("saved transpiled QASM to", out_file)

    if args.qpy is not None:
        out_file = output_path(args.qpy, "qpy")
        with out_file.open("wb") as fd:
            qpy.dump(qcT, fd)
        print("saved transpiled circuit QPY to", out_file)

    qcal_transpiler = QiskitTranspiler(gate_mapper=GATE_MAPPER)
    qcQ = qcal_transpiler.transpile(qcT)[0]

    qpu.run(qcQ, n_shots=args.shots, save=False)
    counts = dict(qcQ.results.counts)
    print("counts", counts)
    print(f"requested shots {args.shots}, received shots {sum(counts.values())}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_args(parser)
    args = parser.parse_args()
    print("arguments:")
    for name, value in vars(args).items():
        print(f"  {name}={value!r}")

    main(args)
