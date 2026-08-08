#!/usr/bin/env python3
"""Run a batched T1 experiment directly on one physical qubit.

Example:

    python run_local_t1.py --qpu IQM --pref_qubit 17
    python run_local_t1.py --qpu IQM --pref_qubit 17 --shots 2000

The experiment prepares |1>, sweeps 42 idle delays from 0 to 123 us in
3 us increments, fits the measured |1> population, and saves the plot under
out/.
"""

import argparse
import os
import time
from pathlib import Path

import numpy as np
import qcal
import qcal.settings as settings
import qiskit
import yaml
from config_utils import get_qubit_pairs
from coupler_flux import apply_coupler_flux, load_coupler_flux
from qcal.backend.qubic.qpu import QubicQPU
from qcal.utils import load_from_pickle
from qcal_transpiler import GenericQiskitTranspiler
from qiskit import QuantumCircuit
from qiskit.transpiler.exceptions import TranspilerError
from scipy.optimize import curve_fit


DELAYS_NS = tuple(range(0, 126_000, 3_000))


def make_circuits(delays_ns=DELAYS_NS):
    circuits = []
    for delay_ns in delays_ns:
        circuit = QuantumCircuit(1, 1)
        circuit.x(0)
        circuit.barrier()
        circuit.delay(delay_ns, 0, unit="ns")
        circuit.barrier()
        circuit.measure(0, 0)
        circuit.metadata = {"delay_ns": delay_ns}
        circuits.append(circuit)
    return circuits


def load_qpu_config(qpu_name, calib_base, physical_qubit):
    """Load all runtime configuration needed to connect to one QPU."""
    active_qpus_path = Path(calib_base) / "active_qpus.yaml"
    assert active_qpus_path.is_file(), f"missing {active_qpus_path}"
    with active_qpus_path.open(encoding="utf-8") as stream:
        active_qpus = yaml.safe_load(stream)

    assert isinstance(active_qpus, dict), f"invalid configuration={active_qpus_path}"
    assert qpu_name in active_qpus, f"qpu {qpu_name} not in {active_qpus_path}"
    chip = active_qpus[qpu_name]
    assert all(key in chip for key in ("calib_tag", "ip", "port"))

    calib_tag = str(chip["calib_tag"])
    config_path = Path(calib_base) / f"{qpu_name}_{calib_tag}"
    assert config_path.is_dir(), f"missing calibration path={config_path}"
    qpu_ip = chip["ip"]
    qpu_port = int(chip["port"])
    basis_gates = chip.get("basis_gates", ["rz", "sx", "cz"])
    assert qpu_ip
    assert 0 < qpu_port < 65536
    assert "rz" in basis_gates, f"basis_gates must preserve Rz angles: {basis_gates}"

    settings.Settings.config_path = str(config_path) + os.sep
    config = qcal.Config()
    assert physical_qubit in config.qubits, (
        f"physical qubit {physical_qubit} not in calibrated qubits={config.qubits}"
    )
    classifier = load_from_pickle(config_path / "ClassificationManager.pkl")
    qubit_pairs = get_qubit_pairs(config_path / "config.yaml")
    biased = apply_coupler_flux(
        config,
        {physical_qubit},
        load_coupler_flux(config_path),
    )
    return (
        config_path,
        calib_tag,
        qpu_ip,
        qpu_port,
        basis_gates,
        qubit_pairs,
        config,
        classifier,
        biased,
    )


def extract_physical_layout(circuit):
    """Return the physical qubit IDs selected by Qiskit."""
    try:
        return circuit._layout.final_index_layout(filter_ancillas=True)
    except AttributeError:
        return list(range(circuit.num_qubits))


def transpile_circuits(
    circuits,
    basis_gates,
    qubit_pairs,
    physical_qubit,
):
    """Transpile and convert the complete T1 circuit batch."""
    try:
        transpiled = qiskit.transpile(
            circuits,
            basis_gates=basis_gates,
            coupling_map=qubit_pairs,
            initial_layout=[physical_qubit],
        )
    except TranspilerError as exc:
        message = str(exc).strip()
        last_line = message.splitlines()[-1] if message else repr(exc)
        raise RuntimeError(f"qiskit.transpile failed: {last_line}") from exc

    assert len(transpiled) == len(circuits)
    for index, circuit in enumerate(transpiled):
        layout = extract_physical_layout(circuit)
        assert layout == [physical_qubit], (
            f"circuit {index} resolved layout={layout}, "
            f"expected [{physical_qubit}]"
        )

    qcal_circuits = GenericQiskitTranspiler(
        delay_unit="ns"
    ).transpile(transpiled).circuits
    assert len(qcal_circuits) == len(circuits)
    return transpiled, qcal_circuits


def execute_circuits(qpu, qcal_circuits, shots):
    """Execute the complete T1 sweep in one QPU sequence."""
    print(
        f"execution started: {len(qcal_circuits)} circuits, "
        f"{shots} shots each"
    )
    execution_start = time.perf_counter()
    qpu.run(qcal_circuits, n_shots=shots, save=False)
    elapsed_seconds = time.perf_counter() - execution_start
    print(f"execution finished, elapsed {int(elapsed_seconds)} sec")

    assert len(qpu.circuits) == len(qcal_circuits), (
        f"QPU returned {len(qpu.circuits)} circuits for "
        f"{len(qcal_circuits)} inputs"
    )
    return [
        {
            str(key): int(value)
            for key, value in circuit.results.dict.items()
        }
        for circuit in qpu.circuits
    ]


def decay(time_us, amplitude, t1_us, offset):
    return amplitude * np.exp(-time_us / t1_us) + offset


def plot_results(
    times_us,
    populations,
    fit_parameters,
    t1_us,
    t1_error_us,
    chip_id,
    physical_qubit,
    calib_tag,
    timestamp,
    filename,
):
    """Save the T1 population and exponential-fit plot."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axis = plt.subplots(figsize=(5, 4), layout="constrained")
    axis.plot(
        times_us,
        populations,
        "o",
        color="blue",
        markersize=7,
        label=f"Meas, Q{physical_qubit}",
    )

    fit_times_us = np.linspace(times_us[0], times_us[-1], 300)
    axis.plot(
        fit_times_us,
        decay(fit_times_us, *fit_parameters),
        color="orange",
        linewidth=2,
        label=(
            rf"Fit: $T_1$ = {t1_us:.1f} "
            rf"({t1_error_us:.1f}) $\mu$s"
        ),
    )
    axis.set_title(
        f"T1  Q{physical_qubit}  {chip_id}_{calib_tag}\n{timestamp}",
        fontsize=20,
    )
    axis.set_xlabel(r"Time ($\mu$s)", fontsize=15)
    axis.set_ylabel(r"$|1\rangle$ Population", fontsize=15)
    axis.tick_params(axis="both", which="major", labelsize=12)
    axis.grid(True)
    axis.legend(fontsize=12)

    fig.savefig(filename, dpi=150)
    plt.close(fig)
    print(f"  saved plot: feh  {filename}")


def analyze_results(
    delays_ns,
    counts,
    chip_id,
    physical_qubit,
    calibration,
    calib_tag,
    shots_per_circuit,
):
    """Fit T1 and save the result plot."""
    assert len(counts) == len(delays_ns)
    received_shots = [sum(result.values()) for result in counts]
    assert all(shots > 0 for shots in received_shots), "received an empty result"

    print("\nPART 3 -- USER: analyse results")
    print("  calibration:", calibration)
    if len(set(received_shots)) == 1:
        shot_summary = f"{received_shots[0]} shots/circuit"
    else:
        shot_summary = (
            f"{min(received_shots)}-{max(received_shots)} shots/circuit "
            f"(requested {shots_per_circuit})"
        )
    print("  shots:", shot_summary)

    times_us = np.asarray(delays_ns, dtype=float) / 1000.0
    populations = np.asarray(
        [
            result.get("1", 0) / sum(result.values())
            for result in counts
        ]
    )
    initial_guess = [
        max(populations[0] - populations[-1], 1e-3),
        max(times_us[-1] / 3.0, 1.0),
        populations[-1],
    ]
    fit_parameters, covariance = curve_fit(
        decay,
        times_us,
        populations,
        p0=initial_guess,
    )
    t1_us = fit_parameters[1]
    t1_error_us = float(np.sqrt(covariance[1][1]))
    print(
        f"  T1 Q{physical_qubit}: {t1_us:.1f} "
        f"(+/- {t1_error_us:.1f}) us"
    )

    output_dir = Path("out")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S_%Z")
    plot_path = output_dir / f"t1_Q{physical_qubit}_{timestamp}.png"
    plot_results(
        times_us,
        populations,
        fit_parameters,
        t1_us,
        t1_error_us,
        chip_id,
        physical_qubit,
        calib_tag,
        timestamp,
        str(plot_path),
    )
    return t1_us, t1_error_us


def add_args(parser):
    parser.add_argument("--qpu", default="IQM", help="QPU queue/chip name.")
    parser.add_argument(
        "--calibBase",
        default="/dataVault2026/qpus_calib",
        help="active_qpus.yaml + calibration folders.",
    )
    parser.add_argument("-n", "--shots", type=int, default=2000)
    parser.add_argument(
        "-q",
        "--pref_qubit",
        type=int,
        required=True,
        help="Physical qubit.",
    )


def main(args):
    assert args.shots > 0
    assert args.pref_qubit >= 0

    (
        config_path,
        calib_tag,
        qpu_ip,
        qpu_port,
        basis_gates,
        qubit_pairs,
        config,
        classifier,
        biased,
    ) = load_qpu_config(args.qpu, args.calibBase, args.pref_qubit)
    print(f"resolved qpu={args.qpu}, ip={qpu_ip}, port={qpu_port}")
    print(f"coupler DC biased: {biased or 'none'}")

    circuits = make_circuits()
    print("last circuit before Qiskit transpiler:")
    print(circuits[-1])
    transpiled, qcal_circuits = transpile_circuits(
        circuits,
        basis_gates,
        qubit_pairs,
        args.pref_qubit,
    )
    print("last circuit after Qiskit transpiler:")
    print(transpiled[-1])
    print(
        f"transpiled {len(transpiled)} circuits as one batch to "
        f"{basis_gates}, physical qubit Q{args.pref_qubit}"
    )

    qpu = QubicQPU(
        config,
        classifier=classifier,
        ip_address=qpu_ip,
        port=qpu_port,
        n_circs_per_seq=100,
        raster_circuits=True,
    )
    counts = execute_circuits(qpu, qcal_circuits, args.shots)
    analyze_results(
        DELAYS_NS,
        counts,
        args.qpu,
        args.pref_qubit,
        config_path.name,
        calib_tag,
        args.shots,
    )


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser()
    add_args(argument_parser)
    parsed_args = argument_parser.parse_args()
    print("arguments:")
    for argument, value in vars(parsed_args).items():
        print(f"  {argument}={value!r}")
    main(parsed_args)
