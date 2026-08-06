#!/usr/bin/env bash

set -euo pipefail

AQDROP_CLIENT_DIR=${AQDROP_CLIENT_DIR:-/pscratch/sd/d/dingpf/aqdrop_workdir/aqdrop-client}
AQDROP_OPERATOR_IMAGE=${AQDROP_OPERATOR_IMAGE:-${AQDROP_IMAGE:-registry.nersc.gov/dseg/aqdrop-operator:202608060}}
AQDROP_CONTAINER_RUNTIME=${AQDROP_CONTAINER_RUNTIME:-podman-hpc}
AQDROP_HOSTNAME=${AQDROP_HOSTNAME:-https://aqdrop-api-dev2.lbl-b59.org}
SFAPI_CLIENT_ID_FILE=${SFAPI_CLIENT_ID_FILE:-$HOME/.ssh/aqdrop-sfapi-client-id}
SFAPI_PRIVATE_KEY_FILE=${SFAPI_PRIVATE_KEY_FILE:-$HOME/.ssh/aqdrop-sfapi-private-key.pem}

test -f "$AQDROP_CLIENT_DIR/pyproject.toml" || {
    echo "Missing AQDrop client checkout: $AQDROP_CLIENT_DIR" >&2
    exit 1
}

test -f "$AQDROP_CLIENT_DIR/aqdrop_operator/job_run_qiskit.py" || {
    echo "Missing $AQDROP_CLIENT_DIR/aqdrop_operator/job_run_qiskit.py" >&2
    exit 1
}

test -f "$SFAPI_CLIENT_ID_FILE" || {
    echo "Missing SFAPI client ID file: $SFAPI_CLIENT_ID_FILE" >&2
    exit 1
}

test -f "$SFAPI_PRIVATE_KEY_FILE" || {
    echo "Missing SFAPI private key file: $SFAPI_PRIVATE_KEY_FILE" >&2
    exit 1
}

echo "Obtaining an SFAPI token with $AQDROP_OPERATOR_IMAGE..." >&2
if ! SFAPI_TOKEN=$("$AQDROP_CONTAINER_RUNTIME" run --rm \
    --volume "$SFAPI_CLIENT_ID_FILE:/run/secrets/sfapi-client-id:ro" \
    --volume "$SFAPI_PRIVATE_KEY_FILE:/run/secrets/sfapi-private-key.pem:ro" \
    "$AQDROP_OPERATOR_IMAGE" \
    aqdrop-generate-sfapi-token \
        --client-id-file /run/secrets/sfapi-client-id \
        --private-key-file /run/secrets/sfapi-private-key.pem); then
    echo "Failed to obtain an SFAPI token" >&2
    exit 1
fi

if [[ ! "$SFAPI_TOKEN" =~ ^[^.]+[.][^.]+[.][^.]+$ ]]; then
    echo "Token helper did not return a valid JWT" >&2
    exit 1
fi
export AQDROP_HOSTNAME SFAPI_TOKEN
echo "SFAPI token obtained; starting the development container." >&2

AQDROP_DEV_BANNER=$(cat <<'EOF'
Local AQDrop client source is mounted at /workspace/aqdrop-client.

Verify the operator source in use:
  python -c "import inspect, aqdrop_operator; print(inspect.getfile(aqdrop_operator))"

Run the locally changed Qiskit operator as a dry run:
  python -m aqdrop_operator.job_run_qiskit --id JOB_ID

Execute and dispatch only after the dry run succeeds:
  python -m aqdrop_operator.job_run_qiskit --id JOB_ID --execJob
EOF
)
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
