# AQDrop

AQDrop is the management system for interaction with the Advanced Quantum Testbed (AQT) at NERSC. It provides a centralized API for job submission, queue management, and member access control.

## Library and Client

The `aqdrop` Python library provides a programmatic interface to the API, allowing users to interact with the quantum testbed via Python scripts.

### Installation

The following command will install the AQDrop library, but will not install Qiskit.
```bash
pip install aqdrop
```

In order to submit Qiskit circuits, install Qiskit manually or include Qiskit in your AQDrop install (ensuring version compatibility) with the following command:
```bash
pip install aqdrop[qiskit]
```

### Basic Usage

See the "examples" directory for examples of basic job submission and retrieval.
```python
import aqdrop
import qiskit

# Initialize the client
client = aqdrop.AqdropClient()

# Submit a Qiskit job
qc = qiskit.QuantumCircuit(1)
qc.h(0)
qc.measure_all()
job = client.submit_qiskit("ideal", qc)
print(f"Job submitted with ID: {job.id}")

# Check job status
status = client.get_job(job_id=job.id)
print(f"Current status: {status.status}")
```

Note that the constructor for AqdropClient requires the user's credentials (including the API hostname). If any credentials are not provided explicitly in the constructor call, AQDrop will check the environment variables AQDROP_USERNAME, AQDROP_PASSWORD, and AQDROP_HOSTNAME.
