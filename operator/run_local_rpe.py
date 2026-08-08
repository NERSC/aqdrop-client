#!/usr/bin/env python3
"""Run a 26-circuit idle-RPE experiment directly on one physical qubit.

Example:

    python run_local_rpe.py --qpu IQM --pref_qubit 20

The experiment uses 256 shots by default and 13 idle depths from 100 ns to
409.6 us. Results are analyzed with pyRPE and saved as an RPE phase plot
under out/.
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
from quapack.pyRPE import RobustPhaseEstimation
from quapack.pyRPE.quantum import Q


DEPTHS = (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096)
IDLE_DURATION_NS = 100


def make_circuits(depths=DEPTHS):
    circuits = []
    for quadrature, first_rotation in (("cos", "ry"), ("sin", "rx")):
        for depth in depths:
            circuit = QuantumCircuit(1, 1)
            getattr(circuit, first_rotation)(np.pi / 2, 0)
            circuit.barrier()
            circuit.delay(depth * IDLE_DURATION_NS, 0, unit="ns")
            circuit.barrier()
            circuit.ry(-np.pi / 2, 0)
            circuit.measure(0, 0)
            circuit.metadata = {"quadrature": quadrature, "depth": depth}
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

    config_path = Path(calib_base) / f"{qpu_name}_{chip['calib_tag']}"
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
    """Transpile and convert the complete RPE circuit batch."""
    try:
        transpiled = qiskit.transpile(
            circuits,
            basis_gates=basis_gates,
            coupling_map=qubit_pairs,
            initial_layout=[physical_qubit],
        )
    except TranspilerError as exc:
        message = str(exc).strip().splitlines()[-1]
        raise RuntimeError(f"qiskit.transpile failed: {message}") from exc

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


def plot_results(
    phase_estimates,
    last_good_index,
    depths,
    chip_id,
    physical_qubit,
    calib_tag,
    timestamp,
    filename,
):
    """Save the RPE angle-error plot."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    depth_array = np.asarray(depths, dtype=float)
    fig, axis = plt.subplots(figsize=(5, 4), layout="constrained")

    if last_good_index >= 0:
        axis.axvline(
            depths[last_good_index],
            linestyle="--",
            color="black",
            label="Last good depth",
        )

    axis.errorbar(
        depth_array,
        phase_estimates,
        yerr=np.pi / (2 * depth_array),
        fmt="o-",
        linewidth=1.5,
        markersize=6,
        elinewidth=0.75,
        capsize=7,
        label="Z",
    )

    max_angle = np.nanmax(np.abs(phase_estimates))
    if max_angle > 0:
        axis.set_ylim(-1.1 * max_angle, 1.1 * max_angle)

    axis.set_title(
        f"RPE  Q{physical_qubit}  {chip_id}_{calib_tag}\n{timestamp}",
        fontsize=20,
    )
    axis.set_xlabel("Circuit Depth", fontsize=15)
    axis.set_ylabel("Angle Error (rad.)", fontsize=15)
    axis.set_xscale("log")
    axis.tick_params(axis="both", which="major", labelsize=12)
    axis.grid(True)
    axis.legend(fontsize=12)

    fig.savefig(filename, dpi=150)
    plt.close(fig)
    print(f"  saved plot: feh  {filename}")


def analyze_results(
    labels,
    counts,
    chip_id,
    physical_qubit,
    calibration,
    calib_tag,
    shots_per_circuit,
    depths=DEPTHS,
):
    assert len(labels) == len(counts)
    assert len(counts) == 2 * len(depths)
    print("\nPART 3 -- USER: analyse results")
    print("  calibration:", calibration)
    received_shots = [sum(result.values()) for result in counts]
    assert all(shots > 0 for shots in received_shots), "received an empty result"
    if len(set(received_shots)) == 1:
        shot_summary = f"{received_shots[0]} shots/circuit"
    else:
        shot_summary = (
            f"{min(received_shots)}-{max(received_shots)} shots/circuit "
            f"(requested {shots_per_circuit})"
        )
    print("  shots:", shot_summary)

    counts_by_experiment = {
        label: {
            "0": int(count.get("0", 0)),
            "1": int(count.get("1", 0)),
        }
        for label, count in zip(labels, counts)
    }
    for depth in depths[:4]:
        print(
            f"  depth {depth:5d}  "
            f"cos {counts_by_experiment[('cos', depth)]}  "
            f"sin {counts_by_experiment[('sin', depth)]}"
        )

    experiment = Q()
    for depth in depths:
        cosine_counts = counts_by_experiment[("cos", depth)]
        sine_counts = counts_by_experiment[("sin", depth)]
        experiment.process_cos(
            depth,
            (cosine_counts["0"], cosine_counts["1"]),
        )
        experiment.process_sin(
            depth,
            (sine_counts["1"], sine_counts["0"]),
        )

    analysis = RobustPhaseEstimation(experiment)
    raw_phases = np.asarray(analysis.angle_estimates)
    phases = (raw_phases + np.pi) % (2 * np.pi) - np.pi
    last_good_index = analysis.check_unif_local(historical=True)

    print(f"  last reliable index: {last_good_index}")
    if last_good_index >= 0:
        last_good_depth = depths[last_good_index]
        trusted_phase = phases[last_good_index]
        trusted_uncertainty = np.pi / (2 * last_good_depth)
        detuning_hz = trusted_phase / (
            2 * np.pi * IDLE_DURATION_NS * 1e-9
        )
        print(f"  last good depth: {last_good_depth}")
        print(
            f"  Z error Q{physical_qubit}: {trusted_phase:.6f} "
            f"(+/- {trusted_uncertainty:.6f}) rad"
        )
        print(f"  estimated detuning: {detuning_hz / 1e3:.3f} kHz")

    output_dir = Path("out")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S_%Z")
    plot_path = output_dir / f"rpe_Q{physical_qubit}_{timestamp}.png"
    plot_results(
        phases,
        last_good_index,
        depths,
        chip_id,
        physical_qubit,
        calib_tag,
        timestamp,
        str(plot_path),
    )


def execute_circuits(qpu, labels, qcal_circuits, shots):
    """Execute the entire circuit list in one QPU sequence."""
    print(
        f"execution started: {len(qcal_circuits)} circuits, "
        f"{shots} shots each"
    )
    execution_start = time.perf_counter()
    qpu.run(qcal_circuits, n_shots=shots, save=False)
    elapsed_seconds = time.perf_counter() - execution_start
    print(f"execution finished, elapsed {int(elapsed_seconds)} sec")

    assert len(qpu.circuits) == len(labels), (
        f"QPU returned {len(qpu.circuits)} circuits for {len(labels)} inputs"
    )
    counts = []
    for qcal_circuit in qpu.circuits:
        result = {
            str(key): int(value)
            for key, value in qcal_circuit.results.dict.items()
        }
        counts.append(result)
    return counts


def add_args(parser):
    parser.add_argument("--qpu", default="IQM", help="QPU queue/chip name.")
    parser.add_argument(
        "--calibBase",
        default="/dataVault2026/qpus_calib",
        help="active_qpus.yaml + calibration folders.",
    )
    parser.add_argument("-n", "--shots", type=int, default=256)
    parser.add_argument(
        "--num_idle_steps",
        type=int,
        default=13,
        help="Number of idle depths to run, from 3 through 13.",
    )
    parser.add_argument("-q", "--pref_qubit", type=int, required=True, help="Physical qubit.")


def main(args):
    assert args.shots > 0
    assert args.pref_qubit >= 0
    assert 3 <= args.num_idle_steps <= 13, (
        f"num_idle_steps must be in [3, 13], got {args.num_idle_steps}"
    )

    (
        config_path,
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

    depths = DEPTHS[: args.num_idle_steps]
    circuits = make_circuits(depths)
    print("last circuit before Qiskit transpiler:")
    print(circuits[-1])
    labels = [
        (circuit.metadata["quadrature"], circuit.metadata["depth"])
        for circuit in circuits
    ]
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
    counts = execute_circuits(
        qpu,
        labels,
        qcal_circuits,
        args.shots,
    )
    config_prefix = f"{args.qpu}_"
    assert config_path.name.startswith(config_prefix)
    calib_tag = config_path.name[len(config_prefix):]
    analyze_results(
        labels,
        counts,
        args.qpu,
        args.pref_qubit,
        config_path.name,
        calib_tag,
        args.shots,
        depths,
    )


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser()
    add_args(argument_parser)
    parsed_args = argument_parser.parse_args()
    print("arguments:")
    for argument, value in vars(parsed_args).items():
        print(f"  {argument}={value!r}")
    main(parsed_args)
