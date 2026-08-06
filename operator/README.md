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

Run one simulator job from the published image in dry-run mode with:

```bash
podman-hpc run --rm \
  -e AQDROP_HOSTNAME \
  -e SFAPI_TOKEN \
  "$AQDROP_IMAGE" aqdrop-run-qiskit --id JOB_ID
```

Add `--execJob` only after the dry run succeeds and execution is explicitly
approved. The supported runner imports
`aqdrop_operator.qiskit_operator.QiskitOperator` from the installed package and
calls `AqdropClient.get_job(job_id)` without legacy keyword arguments.

Outside NERSC, replace `podman-hpc` with the container builder/runtime available
on that host, such as `podman` or Docker.

## Run Local Operator Changes

The published image can supply the Python environment and dependencies while
loading `aqdrop_operator` from a local checkout. This avoids rebuilding the
image or reinstalling the package after each operator-code change.

On `login12`, the repository includes a launcher whose default checkout is
`/pscratch/sd/d/dingpf/aqdrop_workdir/aqdrop-client`:

```bash
cd /pscratch/sd/d/dingpf/aqdrop_workdir/aqdrop-client
operator/launch-dev-container.sh
```

The launcher defaults to `https://aqdrop-api-dev2.lbl-b59.org`. It obtains a
fresh SFAPI token by mounting
`$HOME/.ssh/aqdrop-sfapi-client-id` and
`$HOME/.ssh/aqdrop-sfapi-private-key.pem` into a short-lived instance of the
operator image; the token is validated but not displayed. It then mounts the
checkout read-write, opens an interactive container, and prints the commands
for verifying and running the local Qiskit operator.

Override `AQDROP_HOSTNAME`, `SFAPI_CLIENT_ID_FILE`,
`SFAPI_PRIVATE_KEY_FILE`, `AQDROP_CLIENT_DIR`, `AQDROP_OPERATOR_IMAGE`, or
`AQDROP_CONTAINER_RUNTIME` when different API, credentials, checkout, image, or
runtime values are needed.

From the `aqdrop-client` repository root, mount only the local operator package
and put its parent directory first on Python's import path:

```bash
podman-hpc run --rm \
  -e AQDROP_HOSTNAME \
  -e SFAPI_TOKEN \
  -e PYTHONPATH=/workspace \
  -e PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD/aqdrop_operator:/workspace/aqdrop_operator:ro" \
  "$AQDROP_IMAGE" aqdrop-run-qiskit --id JOB_ID
```

The installed `aqdrop-run-qiskit`, `aqdrop-run-qpu`, and `aqdrop-operator`
commands will import `aqdrop_operator` from `/workspace` instead of the copy
installed in the image. Each command starts a new Python process, so edits made
on the host are used on the next invocation. Keep the mount read-only when the
source is edited on the host.

For an interactive development shell that can edit the checkout, use a
read-write mount:

```bash
podman-hpc run --rm -it \
  -e AQDROP_HOSTNAME \
  -e SFAPI_TOKEN \
  -e PYTHONPATH=/workspace \
  -e PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD/aqdrop_operator:/workspace/aqdrop_operator:rw" \
  "$AQDROP_IMAGE" bash
```

Inside the container, edit files under `/workspace/aqdrop_operator` and rerun
the installed command. Verify which source is active with:

```bash
python -c 'import inspect, aqdrop_operator; print(inspect.getfile(aqdrop_operator))'
```

The path should begin with `/workspace/aqdrop_operator`. If a change also
modifies the base `aqdrop` client package, mount
`$PWD/aqdrop:/workspace/aqdrop:ro` in the same command so both local packages
are loaded together.

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
