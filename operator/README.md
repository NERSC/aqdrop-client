# AQDrop Operator Tooling

This directory owns the operational assets for running AQDrop jobs on Qiskit
simulators and AQT QPUs. The Python runtime is packaged as `aqdrop_operator`;
this directory contains its container, deployment guide, launcher, and manual
hardware smoke test.

Operator API requests use the same SFAPI bearer token as the normal client. The
API grants dispatch and reset operations only after a live NERSC LDAP check for
`aqdrop_operator` membership. No AQDrop-specific username or password is used.
Create a Green client and generate the token as described in
[SFAPI Authentication Setup](../docs/sfapi_authentication.md); Green is
sufficient for operator requests because AQDrop privileges come from LDAP, not
the SFAPI client color.

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

## Container Image

At NERSC, build and run the operator image with `podman-hpc` from the repository
root:

```bash
podman-hpc build \
  -f operator/containers/aqdrop-operator.dockerfile \
  -t aqdrop-operator:latest .
podman-hpc migrate aqdrop-operator:latest
```

The image installs the AQDrop Python package with its operator dependencies, so
it provides both the normal client tool and operator commands without mounting
the source checkout. Verify the client CLI in the image:

```bash
podman-hpc run --rm aqdrop-operator:latest aqdrop
```

This prints the installed client actions. Avoid appending `--help` to this
particular container check because `podman-hpc` consumes that flag as help for
the container runtime.

After exporting the environment variables below, users can run an authenticated
client command directly from the container:

```bash
podman-hpc run --rm \
  -e AQDROP_HOSTNAME \
  -e SFAPI_TOKEN \
  aqdrop-operator:latest aqdrop queue_list
```

Outside NERSC, replace `podman-hpc` with the container builder/runtime available
on that host, such as `podman` or Docker.

## Environment

Set these variables before starting a runner:

```bash
export AQDROP_HOSTNAME=https://<aqdrop-api-host>
export SFAPI_TOKEN=<current-sfapi-token>
export QUBIC_CALIB_BASE_PATH=/path/to/qpus_calib
```

`QUBIC_CALIB_BASE_PATH` is required only for QPU execution and must contain
`active_qpus.yaml` plus each active calibration directory.

See [docs/setup.md](docs/setup.md) for the `qubic3` `podman-hpc` workflow. The script
[tools/qpu_smoke.py](tools/qpu_smoke.py) runs directly against a QPU
without claiming an AQDrop job and is intended only for manual hardware checks.
