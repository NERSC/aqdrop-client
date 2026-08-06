#!/usr/bin/env bash

set -euo pipefail

: "${AQDROP_HOSTNAME:?Set AQDROP_HOSTNAME to the AQDrop API URL}"
: "${SFAPI_TOKEN:?Set SFAPI_TOKEN to a current SFAPI token}"

AQDROP_CLIENT_DIR=${AQDROP_CLIENT_DIR:-/pscratch/sd/d/dingpf/aqdrop_workdir/aqdrop-client}
AQDROP_OPERATOR_IMAGE=${AQDROP_OPERATOR_IMAGE:-${AQDROP_IMAGE:-registry.nersc.gov/dseg/aqdrop-operator:202608060}}
AQDROP_CONTAINER_RUNTIME=${AQDROP_CONTAINER_RUNTIME:-podman-hpc}

test -f "$AQDROP_CLIENT_DIR/pyproject.toml" || {
    echo "Missing AQDrop client checkout: $AQDROP_CLIENT_DIR" >&2
    exit 1
}

test -f "$AQDROP_CLIENT_DIR/aqdrop_operator/job_run_qiskit.py" || {
    echo "Missing $AQDROP_CLIENT_DIR/aqdrop_operator/job_run_qiskit.py" >&2
    exit 1
}

AQDROP_DEV_BANNER=$'Local AQDrop client source is mounted at /workspace/aqdrop-client.\n\nVerify the operator source in use:\n  python -c '\''import inspect, aqdrop_operator; print(inspect.getfile(aqdrop_operator))'\''\n\nRun the locally changed Qiskit operator as a dry run:\n  python -m aqdrop_operator.job_run_qiskit --id JOB_ID\n\nExecute and dispatch only after the dry run succeeds:\n  python -m aqdrop_operator.job_run_qiskit --id JOB_ID --execJob\n'
export AQDROP_DEV_BANNER

exec "$AQDROP_CONTAINER_RUNTIME" run --rm -it \
    -e AQDROP_HOSTNAME \
    -e SFAPI_TOKEN \
    -e AQDROP_DEV_BANNER \
    -e PYTHONPATH=/workspace/aqdrop-client \
    -e PYTHONDONTWRITEBYTECODE=1 \
    --volume "$AQDROP_CLIENT_DIR:/workspace/aqdrop-client:rw" \
    --workdir /workspace/aqdrop-client \
    "$AQDROP_OPERATOR_IMAGE" \
    /bin/bash -lc 'printf "%s\n" "$AQDROP_DEV_BANNER"; exec /bin/bash -i'
