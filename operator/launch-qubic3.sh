#!/usr/bin/env bash

set -euo pipefail

: "${AQDROP_HOSTNAME:?Set AQDROP_HOSTNAME to the AQDrop API URL}"
: "${SFAPI_TOKEN:?Set SFAPI_TOKEN to a current SFAPI token}"

QUBIC_CALIB_BASE_PATH=${QUBIC_CALIB_BASE_PATH:-$HOME/dataVault2026/qpus_calib}
AQDROP_OPERATOR_IMAGE=${AQDROP_OPERATOR_IMAGE:-aqdrop-operator:latest}
AQDROP_CONTAINER_RUNTIME=${AQDROP_CONTAINER_RUNTIME:-podman-hpc}

test -f "$QUBIC_CALIB_BASE_PATH/active_qpus.yaml" || {
    echo "Missing $QUBIC_CALIB_BASE_PATH/active_qpus.yaml" >&2
    exit 1
}

exec "$AQDROP_CONTAINER_RUNTIME" run --rm -it \
    --network host \
    -e AQDROP_HOSTNAME \
    -e SFAPI_TOKEN \
    -e QUBIC_CALIB_BASE_PATH=/opt/qpus_calib \
    -e HOME \
    -e DISPLAY \
    --volume "$HOME:$HOME" \
    --volume "$QUBIC_CALIB_BASE_PATH:/opt/qpus_calib:ro" \
    --workdir "$HOME" \
    "$AQDROP_OPERATOR_IMAGE" /bin/bash
