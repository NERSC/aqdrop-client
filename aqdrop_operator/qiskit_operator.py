import time

import qiskit
from qiskit_aer import AerSimulator
from qiskit_ibm_runtime.fake_provider import FakeTorino

from aqdrop import AqdropClient, defs

from .qpy_utils import decode_circuits, encode_circuits


class QiskitOperator:
    def __init__(self, verb: int = 1, execJob: bool = False):
        self.verb = verb
        self.execJob = execJob
        self.client = AqdropClient()

        # State filled in by the pipeline steps below.
        self.job_id = None
        self.job = None
        self.circL = None
        self.inputMD = None
        self.backend = None
        self.transpile_backend = None
        self.calib_ver = None
        self.basis_gates = None
        self.transpiled = None
        self.counts = None
        self.shots = None
        self.num_qubits = None
        self.num_2q_gates = None
        self.exec_time = None
        self.exec_date = None
        self.output = None


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


    def simulator_select(self):
        assert self.job is not None
        queue_name = self.job["queue_name"]

        queue_info = self.client.get_queue(queue_name)
        supported_queues = ("ideal", "noisy")
        simu_queues = [
            queue["name"]
            for queue in self.client.list_queues()
            if queue["type"] == defs.QueueType.SIMU and queue["name"] in supported_queues
        ]
        if queue_info["type"] != defs.QueueType.SIMU or queue_name not in supported_queues:
            print(f'Job {self.job_id} was submitted to queue={queue_name}, type={queue_info["type"]}')
            print(f'job_run_qiskit.py serves only Qiskit simulator queues: {simu_queues}')
            raise SystemExit(1)

        if queue_name == "ideal":
            self.backend = AerSimulator(method="statevector")
            self.transpile_backend = self.backend
            self.calib_ver = "ideal_statevector"
            self.basis_gates = list(self.backend.configuration().basis_gates)
        else:
            fake_backend = FakeTorino()
            self.backend = AerSimulator.from_backend(fake_backend)
            self.transpile_backend = fake_backend
            self.calib_ver = fake_backend.name
            self.basis_gates = list(fake_backend.operation_names)

        print(f'qiskit_backend_selected: queue={queue_name}, backend={self.backend.name}')
        if self.verb > 1:
            print('basis_gates', self.basis_gates)


    def simulator_run_job(self):
        assert self.circL is not None
        assert self.backend is not None
        assert self.transpile_backend is not None

        self.exec_date = time.strftime("%Y%m%d_%H%M%S_%Z")
        requested_shots = self.inputMD["shots"]
        if isinstance(requested_shots, int):
            requested_shots = [requested_shots] * len(self.circL)

        transpiled = []
        counts = []
        shots = []
        num_qubits = []
        num_2q_gates = []
        exec_time = []
        for circuit_id, qc in enumerate(self.circL):
            start_time = time.perf_counter()
            qcT, count = self._run_circuit(qc, requested_shots[circuit_id])
            if self.execJob:
                print(f"qcT circuit_id={circuit_id}")
                print(qcT)
            exec_time.append(time.perf_counter() - start_time)
            transpiled.append(qcT)
            counts.append(count)
            shots.append(sum(count.values()))
            num_qubits.append(qcT.num_qubits)
            num_2q_gates.append(sum(1 for instruction in qcT.data if len(instruction.qubits) == 2))

        self.transpiled = transpiled
        self.counts = counts
        self.shots = shots
        self.num_qubits = num_qubits
        self.num_2q_gates = num_2q_gates
        self.exec_time = exec_time
        print(f'qiskit_run_job: executed {len(transpiled)} circuits')
        tot_shots_requested = sum(requested_shots)
        tot_shots_received = sum(shots)
        tot_exec_time = sum(exec_time)
        print(f'qiskit_run_job: {len(transpiled)} circuits, total exec time {tot_exec_time:.1f} sec, requested shots {tot_shots_requested}, received shots {tot_shots_received}')


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


    def _run_circuit(self, qc: qiskit.QuantumCircuit, num_shots: int):
        qcT = qiskit.transpile(qc, backend=self.transpile_backend)
        if self.execJob:
            result = self.backend.run(qcT, shots=num_shots).result()
            counts = {str(key): int(value) for key, value in result.get_counts().items()}
        else:
            counts = {'skip_run': 0}
        return (qcT, counts)
