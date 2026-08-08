#!/usr/bin/env python3

"""Run a Bell circuit directly on one Qubic QPU and print counts."""

# qcal imports
import qcal.settings as settings
from qcal.utils import load_from_pickle
import qcal
from qcal.backend.qubic.qpu import QubicQPU

from qcal.interface.superstaq.transpiler import QiskitTranspiler
from qcal.circuit import Barrier
from qcal.gate.single_qubit import Meas, X90,Z
from qcal.gate.two_qubit import CZ
from aqdrop_operator.config_utils import get_qubit_pairs

import argparse
import os

import qiskit
import yaml
from qiskit import QuantumCircuit, qasm2, qpy
from qiskit.transpiler.exceptions import TranspilerError


GATE_MAPPER = {
    'barrier':  Barrier,
    'measure':  Meas,
    'cz':       CZ,
    'sx':       X90,
    'p':        Z,
}

def circ_bell(qct=0,qtg=1):  #WORKS
    qc = QuantumCircuit(3, 2)
    qc.h(qct)
    qc.cx(qct, qtg)
    #qc.barrier([0,2])
    #qc.h(qtg);qc.h(qtg)
    qc.measure(qct, 0)
    qc.measure(qtg, 1)
    return qc


def circ_Nq(nq):
    qc = QuantumCircuit(nq,nq)
    qc.h(0)
    qc.h(1)
    #qc.cx(0,1)
    #qc.x(0)
    #qc.x(1)
    #qc.barrier()
    for i in range(0,nq):
        qc.measure(i,i)

    return qc

def extract_physical_layout(qc):
    """Extracts physical IDs."""
    try:
        physQubitLayout = qc._layout.final_index_layout(filter_ancillas=True)
        nqTot = len(physQubitLayout)
    except:
        nqTot = qc.num_qubits
        physQubitLayout = [i for i in range(nqTot)]
    return physQubitLayout


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
    p("--calibBase", default="/home/balewski/dataVault2026/qpus_calib", help="active_qpus.yaml + calibration folders.")
    p("-n", "--shots", type=int, default=2000, help="Requested shots.")
    p("-q", "--pref_qubits", type=int, nargs="+", default=None, metavar="2 1 0", help="Physical qubits list for transpiler.")
    p("--qasm", default=None, metavar="NAME", help="Save transpiled QASM to out/NAME.qasm.")
    p("--qpy", default=None, metavar="NAME", help="Save transpiled circuit to out/NAME.qpy.")


def load_qpu_config(qpu_name: str, calib_base: str):
    assert os.path.isdir(calib_base), f"missing calibration base path={calib_base}"

    active_qpus_path = os.path.join(calib_base, "active_qpus.yaml")
    with open(active_qpus_path) as fd:
        qubicCalibD = yaml.safe_load(fd)

    assert qpu_name in qubicCalibD, f"qpu {qpu_name} not in {active_qpus_path}"
    chipD = qubicCalibD[qpu_name]
    calib_ver = f"{qpu_name}_{chipD['calib_tag']}"
    settings_config_path = os.path.join(calib_base, calib_ver + "/")
    assert os.path.isdir(settings_config_path), f"missing calibration path={settings_config_path}"

    qpu_ip = chipD['ip']
    qpu_port = int(chipD['port'])
    return settings_config_path, qpu_ip, qpu_port

def main(args):
    settings_config_path, qpu_ip, qpu_port = load_qpu_config(args.qpu, args.calibBase)
    settings.Settings.config_path = settings_config_path
    settings_config_path = settings_config_path.rstrip("/")

    classifier = load_from_pickle(settings_config_path + "/ClassificationManager.pkl")

    qcal_cfg = qcal.Config()
    qpu = QubicQPU(qcal_cfg, classifier=classifier, ip_address=qpu_ip, port=qpu_port)

    qubit_pairs = get_qubit_pairs(f"{settings_config_path}/config.yaml")

    basis_gates = ['p', 'sx', 'cz']
    pref_qubits = args.pref_qubits
    print("basis_gates", basis_gates)
    print("qubit_pairs", qubit_pairs)
    print("pref_qubits", pref_qubits)

    qc = circ_bell()  #WORKS
    #qc = circ_bell(qct=2,qtg=1)  #WORKS
    #qc = circ_bell(qct=2,qtg=0)
    #qc = circ_Nq(2)

    print("input circuit:")
    print(qc)
    if pref_qubits is not None:
        assert qc.num_qubits==len(pref_qubits), f"num_qubits={qc.num_qubits} != pref_qubits={pref_qubits}"

    qcT = qiskit_transpile(
        qc,
        basis_gates=basis_gates,
        coupling_map=qubit_pairs,
        initial_layout=pref_qubits,
    )

    phys_qubits=extract_physical_layout(qcT)
    print("transpiled circuit to gates=:%s, phys qubits:%s"%(basis_gates,phys_qubits))
    print(qcT)
    if args.qasm is not None:
        qasm_str = qasm2.dumps(qcT)
        outF = os.path.join("out", f'{args.qasm}.qasm')
        with open(outF, "w") as fd:
            fd.write(qasm_str)
        print("saved transpiled QASM to", outF)

    if args.qpy is not None:
        outF = os.path.join("out", f"{args.qpy}.qpy")
        with open(outF, "wb") as fd:
            qpy.dump(qcT, fd)
        print("saved transpiled circuit QPY to", outF)

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
    for arg in vars(args):
        print(arg, getattr(args, arg))

    main(args)
