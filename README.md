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

