#!/usr/bin/env bash

set -euo pipefail

: "${AQDROP_HOSTNAME:?Set AQDROP_HOSTNAME to the AQDrop API URL}"
: "${SFAPI_TOKEN:?Set SFAPI_TOKEN to a current SFAPI token}"

CLIENT_DIR=${AQDROP_CLIENT_DIR:-$HOME/myAQDrop/aqdrop-client}
QUBIC_CALIB_BASE_PATH=${QUBIC_CALIB_BASE_PATH:-$HOME/dataVault2026/qpus_calib}
AQDROP_OPERATOR_IMAGE=${AQDROP_OPERATOR_IMAGE:-aqdrop-operator:latest}

test -d "$CLIENT_DIR/aqdrop_operator" || {
    echo "Missing aqdrop-client checkout at $CLIENT_DIR" >&2
    exit 1
}
test -f "$QUBIC_CALIB_BASE_PATH/active_qpus.yaml" || {
    echo "Missing $QUBIC_CALIB_BASE_PATH/active_qpus.yaml" >&2
    exit 1
}

exec podman run --rm -it \
    --network host \
    -e AQDROP_HOSTNAME \
    -e SFAPI_TOKEN \
    -e QUBIC_CALIB_BASE_PATH=/opt/qpus_calib \
    -e HOME \
    -e DISPLAY \
    --volume "$HOME:$HOME" \
    --volume "$CLIENT_DIR:/workspace/aqdrop-client" \
    --volume "$QUBIC_CALIB_BASE_PATH:/opt/qpus_calib:ro" \
    --workdir /workspace/aqdrop-client \
    "$AQDROP_OPERATOR_IMAGE" /bin/bash
