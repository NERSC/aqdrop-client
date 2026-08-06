# qcal imports
try:
    import qcal.settings as settings
    from qcal.utils import load_from_pickle
    import qcal
    from qcal.backend.qubic.qpu import QubicQPU
except ModuleNotFoundError as exc:
    if exc.name != "qcal":
        raise
    print("Install the AQDrop operator dependencies with: pip install '.[operator]'")
    raise SystemExit(1)

import qiskit
import os
import time
import yaml
from qiskit.transpiler.exceptions import TranspilerError

from aqdrop import AqdropClient, defs
from .config_utils import get_qubit_pairs
from .coupler_flux import apply_coupler_flux, load_coupler_flux
from .qcal_transpiler import GenericQiskitTranspiler
from .qpy_utils import decode_circuits, encode_circuits


def qiskit_transpile(qc, **transpile_kw):
    """Wrap qiskit.transpile and report the useful part of a transpiler error."""
    try:
        return qiskit.transpile(qc, **transpile_kw)
    except TranspilerError as exc:
        msg = str(exc).strip()
        if msg:
            last_line = msg.split("\n")[-1].strip()
        else:
            last_line = repr(exc)
        print("qiskit.transpile failed:", last_line)
        raise SystemExit(1)


def extract_physical_layout(qc):
    """Extracts physical IDs."""
    layout = qc._layout.final_index_layout(filter_ancillas=True)
    return [int(qubit) for qubit in layout]


def _extract_counts(qcal_circuit):
    """Return ordinary string/int counts from a completed qcal circuit."""
    return {
        str(state): int(count)
        for state, count in qcal_circuit.results.dict.items()
    }


class AqdropOperator:
    """Pipeline-style operator that pulls a queued AQDrop job, runs it on a
    QubicQPU, and pushes the result back. The pipeline is intentionally split
    into discrete steps that can be called from job_run_qpu.py:

        pull_job_input  ->  parse_job_input  ->  qpu_connect
                        ->  qpu_run_job      ->  assemble_job_output
                        ->  push_job_output
    """

    def __init__(self, verb: int = 1, execJob: bool = False):
        self.verb = verb
        self.execJob = execJob
        self.client = AqdropClient()
        self._transpile = qiskit_transpile

        # State filled in by the pipeline steps below.
        self.job_id = None
        self.job = None
        self.circL = None
        self.inputMD = None
        self.calib_ver = None
        self.transpiled = None
        self.counts = None
        self.shots = None
        self.num_qubits = None
        self.num_2q_gates = None
        self.exec_time = None
        self.exec_date = None
        self.output = None
        self.phys_qubits = None
        self.qpu = None
        self.biased_couplers = None


    def pull_job_input(self, job_id: int) -> dict:
        job = self.client.get_job(job_id)
        if not job:
            print(f'Job {job_id} was not found in AQDrop.')
            print('Check the job ID or submit a new job before running the operator.')
            raise SystemExit(1)
        if job['status'] != defs.JobStatus.QUEUED:
            print(f'Job {job_id} is status={job["status"]}, expected status={defs.JobStatus.QUEUED.value}')
            raise SystemExit(1)
        self.job_id = job_id
        self.job = job
        print(f'pulled job_id={job_id} from queue={job["queue_name"]}, status={job["status"]}')
        return job


    def parse_job_input(self):
        assert self.job is not None
        job_input = self.job["input"]
        self.circL = decode_circuits(job_input["circ_inp_qpy"])
        self.inputMD = {k: v for k, v in job_input.items() if k != "circ_inp_qpy"}
        print(f'parsed job_input: {len(self.circL)} circuits, inputMD keys={list(self.inputMD)}')
        return self.circL, self.inputMD


    def qpu_connect(self):
        assert self.job is not None
        chip_name = self.job["queue_name"]

        queue_info = self.client.get_queue(chip_name)
        if queue_info["type"] != defs.QueueType.QPU:
            qpu_queues = [
                queue["name"]
                for queue in self.client.list_queues()
                if queue["type"] == defs.QueueType.QPU
            ]
            print(f'Job {self.job_id} was submitted to queue={chip_name}, type={queue_info["type"]}')
            print(f'job_run_qpu.py serves only QPU queues: {qpu_queues}')
            raise SystemExit(1)

        qubicCalibPath = os.getenv('QUBIC_CALIB_BASE_PATH')
        if self.verb > 1:
            print('qubicCalibPath', qubicCalibPath)
        assert qubicCalibPath and os.path.isdir(qubicCalibPath)

        active_qpus_path = os.path.join(qubicCalibPath, "active_qpus.yaml")
        with open(active_qpus_path) as fd:
            qubicCalibD = yaml.safe_load(fd)

        if chip_name not in qubicCalibD:
            print(f'Job {self.job_id} was submitted to queue={chip_name}')
            print(f'job_run_qpu.py can serve active QPU queues: {list(qubicCalibD)}')
            raise SystemExit(1)
        chipD = qubicCalibD[chip_name]
        self.calib_ver = f"{chip_name}_{chipD['calib_tag']}"
        self.settings_config_path = os.path.join(qubicCalibPath, self.calib_ver + "/")
        assert os.path.isdir(self.settings_config_path)

        self.qpu_ip = chipD['ip']
        self.qpu_port = int(chipD['port'])

        settings.Settings.config_path = self.settings_config_path
        self.settings_config_path = self.settings_config_path.rstrip("/")
        self.cfg = qcal.Config()

        classifier = load_from_pickle(self.settings_config_path + "/ClassificationManager.pkl")

        self.basis_gates = chipD["basis_gates"]
        if "rz" not in self.basis_gates:
            raise RuntimeError(
                f"QPU queue {chip_name} must define an rz-preserving basis, "
                f"got {self.basis_gates}"
        )
        self.qubit_pairs = get_qubit_pairs(f"{self.settings_config_path}/config.yaml")
        coupler_flux = load_coupler_flux(self.settings_config_path)
        pref_qubits = self.inputMD["pref_qubits"]
        if not isinstance(pref_qubits, list) or not pref_qubits:
            raise ValueError(
                "job input must specify a non-empty pref_qubits list, "
                f"got {pref_qubits}"
            )
        calibrated_qubits = set(self.cfg.qubits)
        if not set(pref_qubits) <= calibrated_qubits:
            raise RuntimeError(
                f"job requested physical qubits={pref_qubits}, "
                f"but calibrated qubits={sorted(calibrated_qubits)}"
            )
        self.biased_couplers = apply_coupler_flux(
            self.cfg,
            pref_qubits,
            coupler_flux,
        )
        print(f"coupler DC biased: {self.biased_couplers or 'none'}")
        self.qpu = QubicQPU(
            self.cfg,
            classifier=classifier,
            ip_address=self.qpu_ip,
            port=self.qpu_port,
            n_circs_per_seq=100,
            raster_circuits=True,
        )

        print(f'qpu_connected to {chip_name}')
        if self.verb > 1:
            print('basis_gates', self.basis_gates)
            print('qubit_pairs', self.qubit_pairs)


    def qpu_run_job(self):
        assert self.circL is not None
        assert self.qpu is not None

        self.exec_date = time.strftime("%Y%m%d_%H%M%S_%Z")
        requested_shots = self.inputMD["shots"]
        if not isinstance(requested_shots, list) or len(requested_shots) != len(self.circL):
            raise ValueError(
                "job input must contain one shot count per circuit: "
                f"shots={requested_shots}, circuits={len(self.circL)}"
            )
        if any(shots <= 0 for shots in requested_shots):
            raise ValueError(f"all shot counts must be positive: {requested_shots}")

        pref_qubits = self.inputMD["pref_qubits"]
        transpile_kw = {
            "basis_gates": self.basis_gates,
            "coupling_map": self.qubit_pairs,
            "initial_layout": pref_qubits,
        }
        if any(qc.num_qubits != len(pref_qubits) for qc in self.circL):
            raise ValueError(
                f"pref_qubits={pref_qubits} does not match every "
                "circuit's qubit count"
            )

        transpile_start = time.perf_counter()
        transpiled = self._transpile(self.circL, **transpile_kw)
        transpiled = list(transpiled)
        if len(transpiled) != len(self.circL):
            raise RuntimeError(
                f"Qiskit transpiler returned {len(transpiled)} circuits for "
                f"{len(self.circL)} inputs"
            )

        phys_qubits = [extract_physical_layout(qc) for qc in transpiled]
        for circuit_id, layout in enumerate(phys_qubits):
            if layout != pref_qubits:
                raise RuntimeError(
                    f"circuit {circuit_id} resolved layout={layout}, "
                    f"expected {pref_qubits}"
                )

        delay_unit = self.inputMD["delay_unit"]
        qcal_circuits = GenericQiskitTranspiler(
            delay_unit=delay_unit
        ).transpile(transpiled).circuits
        if len(qcal_circuits) != len(transpiled):
            raise RuntimeError(
                f"qcal transpiler returned {len(qcal_circuits)} circuits for "
                f"{len(transpiled)} inputs"
            )

        transpile_elapsed = time.perf_counter() - transpile_start
        exec_time = [transpile_elapsed / len(transpiled)] * len(transpiled)
        counts = [None] * len(qcal_circuits)
        if self.execJob:
            shot_groups = {}
            for circuit_id, num_shots in enumerate(requested_shots):
                shot_groups.setdefault(num_shots, []).append(circuit_id)

            for num_shots, circuit_ids in shot_groups.items():
                circuit_batch = [qcal_circuits[index] for index in circuit_ids]
                print(
                    f"execution started: {len(circuit_batch)} circuits, "
                    f"{num_shots} shots each"
                )
                execution_start = time.perf_counter()
                self.qpu.run(circuit_batch, n_shots=num_shots, save=False)
                execution_elapsed = time.perf_counter() - execution_start
                returned_circuits = list(self.qpu.circuits)
                if len(returned_circuits) != len(circuit_batch):
                    raise RuntimeError(
                        f"QPU returned {len(returned_circuits)} circuits for "
                        f"{len(circuit_batch)} inputs"
                    )
                per_circuit_elapsed = execution_elapsed / len(circuit_ids)
                for circuit_id, qcal_circuit in zip(
                    circuit_ids, returned_circuits
                ):
                    counts[circuit_id] = _extract_counts(qcal_circuit)
                    exec_time[circuit_id] += per_circuit_elapsed
                print(
                    f"execution finished, elapsed {int(execution_elapsed)} sec"
                )
        else:
            counts = [{"skip_run": 0} for _ in qcal_circuits]

        shots = [sum(count.values()) for count in counts]
        num_qubits = [qc.num_qubits for qc in transpiled]
        num_2q_gates = [
            sum(
                1
                for instruction in qc.data
                if len(instruction.qubits) == 2
                and instruction.operation.name != "barrier"
            )
            for qc in transpiled
        ]

        self.transpiled = transpiled
        self.counts = counts
        self.shots = shots
        self.num_qubits = num_qubits
        self.num_2q_gates = num_2q_gates
        self.exec_time = exec_time
        self.phys_qubits = phys_qubits
        print(f'qpu_run_job: executed {len(transpiled)} circuits')
        tot_shots_requested = sum(requested_shots)
        tot_shots_received = sum(shots)
        tot_exec_time = sum(exec_time)
        print(f'qpu_run_job: {len(transpiled)} circuits, total exec time {tot_exec_time:.1f} sec, requested shots {tot_shots_requested}, received shots {tot_shots_received}')


    def assemble_job_output(self) -> dict:
        assert self.transpiled is not None
        assert self.calib_ver is not None
        assert self.exec_date is not None
        tot_shots = sum(self.shots)
        tot_exec_time = sum(self.exec_time)
        self.output = {
            "counts": self.counts,
            "shots": self.shots,
            "num_qubits": self.num_qubits,
            "num_2q_gates": self.num_2q_gates,
            "exec_time": self.exec_time,
            "tot_shots": tot_shots,
            "tot_exec_time": tot_exec_time,
            "calib_ver": self.calib_ver,
            "exec_date": self.exec_date,
            "basis_gates": self.basis_gates,
            "phys_qubits": self.phys_qubits,
            "circ_transp_qpy": encode_circuits(self.transpiled),
        }
        print(f'assembled job_output for {len(self.counts)} circuits')
        return self.output


    def push_job_output(self) -> dict:
        assert self.output is not None
        assert self.job_id is not None
        job = self.client.dispatch_job(self.job_id, defs.JobStatus.SUCCESS, self.output)
        print(f'pushed job_output for job_id={self.job_id}, status={defs.JobStatus.SUCCESS.value}')
        return job
