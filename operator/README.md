# AQDrop Operator Tooling

This directory owns the operational assets for running AQDrop jobs on Qiskit
simulators and AQT QPUs. The Python runtime is packaged as `aqdrop_operator`;
this directory contains its container, deployment guide, launcher, and manual
hardware smoke test.

Operator API requests use the same SFAPI bearer token as the normal client. The
API grants dispatch and reset operations only after a live NERSC LDAP check for
`aqdrop_operator` membership. No AQDrop-specific username or password is used.

## Install

From the repository root:

```bash
python -m pip install ".[operator]"
```

This installs three commands:

- `aqdrop-operator`: poll queued jobs and dispatch them to the correct runner
- `aqdrop-run-qiskit --id JOB_ID`: run one simulator job
- `aqdrop-run-qpu --id JOB_ID`: run one QPU job

Both one-job runners are dry runs unless `--execJob` is supplied.

## Environment

Set these variables before starting a runner:

```bash
export AQDROP_HOSTNAME=https://<aqdrop-api-host>
export NERSC_OIDC_TOKEN=<current-sfapi-token>
export QUBIC_CALIB_BASE_PATH=/path/to/qpus_calib
```

`QUBIC_CALIB_BASE_PATH` is required only for QPU execution and must contain
`active_qpus.yaml` plus each active calibration directory.

See [docs/setup.md](docs/setup.md) for the `qubic3` Podman workflow. The script
[tools/qpu_smoke.py](tools/qpu_smoke.py) runs directly against a QPU
without claiming an AQDrop job and is intended only for manual hardware checks.
