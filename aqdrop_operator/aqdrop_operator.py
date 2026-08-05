# qcal imports
try:
    import qcal.settings as settings
    from qcal.utils import load_from_pickle
    import qcal
    from qcal.backend.qubic.qpu import QubicQPU

    from qcal.interface.superstaq.transpiler import QiskitTranspiler
    from qcal.circuit import Barrier
    from qcal.gate.single_qubit import Meas, X90, Z
    from qcal.gate.two_qubit import CZ
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
    try:
        physQubitLayout = qc._layout.final_index_layout(filter_ancillas=True)
        nqTot = len(physQubitLayout)
    except:
        nqTot = qc.num_qubits
        physQubitLayout = [i for i in range(nqTot)]
    return physQubitLayout


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

        self.gate_mapper = {
            'barrier':  Barrier,
            'measure':  Meas,
            'cz':       CZ,
            'sx':       X90,
            'p':        Z,
        }

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

        self.qcal_cfg = qcal.Config()
        self.qpu = QubicQPU(self.qcal_cfg, classifier=classifier, ip_address=self.qpu_ip, port=self.qpu_port)

        self.basis_gates = ['p', 'sx', 'cz']
        self.qubit_pairs = get_qubit_pairs(f"{self.settings_config_path}/config.yaml")

        print(f'qpu_connected to {chip_name}')
        if self.verb > 1:
            print('basis_gates', self.basis_gates)
            print('qubit_pairs', self.qubit_pairs)


    def qpu_run_job(self):
        assert self.circL is not None
        assert self.qpu is not None

        self.exec_date = time.strftime("%Y%m%d_%H%M%S_%Z")
        transpiled = []
        counts = []
        shots = []
        num_qubits = []
        num_2q_gates = []
        exec_time = []
        phys_qubits = []
        requested_shots = self.inputMD["shots"]
        if isinstance(requested_shots, int):
            requested_shots = [requested_shots] * len(self.circL)

        for circuit_id, qc_ideal in enumerate(self.circL):
            start_time = time.perf_counter()
            qcT, count = self._run_circuit(qc_ideal, requested_shots[circuit_id])
            if self.execJob:
                print(f"qcT circuit_id={circuit_id}")
                print(qcT)
            exec_time.append(time.perf_counter() - start_time)
            transpiled.append(qcT)
            counts.append(count)
            shots.append(sum(count.values()))
            num_qubits.append(qcT.num_qubits)
            num_2q_gates.append(sum(1 for instruction in qcT.data if len(instruction.qubits) == 2))
            phys_qubits.append(extract_physical_layout(qcT))

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


    # NOTE: for now we assume that any job is a qiskit job; this may change later
    def _run_circuit(self, qc: qiskit.QuantumCircuit, num_shots: int):
        pref_qubits = self.inputMD.get("pref_qubits")
        transpile_kw = dict(basis_gates=self.basis_gates, coupling_map=self.qubit_pairs)
        if pref_qubits is not None:
            #pref_qubits = [2,1] #tmp for testing
            print("pref_qubits", pref_qubits, "qc.num_qubits", qc.num_qubits)
            transpile_kw["initial_layout"] = pref_qubits

        qcT = self._transpile(qc, **transpile_kw)

        qcal_transpiler = QiskitTranspiler(gate_mapper=self.gate_mapper)
        qcQ = qcal_transpiler.transpile(qcT)[0]

        if self.execJob:
            self.qpu.run(qcQ, n_shots=num_shots)
            counts = dict(qcQ.results.counts)
        else:
            counts = {'skip_run': 0}
        return (qcT, counts)
