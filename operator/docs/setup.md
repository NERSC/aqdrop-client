# AQDrop Operator Setup on qubic3

This guide configures the client-side AQDrop operator runtime on `qubic3`.

## Prerequisites

The operator needs:

- NERSC LDAP membership in both `aqdrop_users` and `aqdrop_operator`
- access to `qubic3` and the selected QPU calibration data
- a current SFAPI bearer token
- the AQDrop API hostname

The API verifies the username encoded in the SFAPI token and performs a live
LDAP query for every dispatch or reset. There is no separate AQDrop username,
password, or locally managed operator account.

## Checkout and Build

```bash
ssh qubic3
git clone git@github.com:NERSC/aqdrop-client.git
cd aqdrop-client
podman build \
  -f operator/containers/aqdrop-operator.dockerfile \
  -t aqdrop-operator:latest .
```

For an existing checkout, pull the intended branch before rebuilding.

## Credentials and Calibration

Store credentials in a private shell file outside the repository:

```bash
export AQDROP_HOSTNAME=https://<aqdrop-api-host>
export NERSC_OIDC_TOKEN=<current-sfapi-token>
export QUBIC_CALIB_BASE_PATH=$HOME/dataVault2026/qpus_calib
```

Restrict the file with `chmod 600`. Do not commit tokens or include them in the
container image. The calibration path must contain `active_qpus.yaml`; each
entry supplies the queue's calibration tag, IP address, and port.

## Start the Container

From the repository root, source the credential file and launcher:

```bash
source ~/.ssh/aqdrop-operator.creds
export AQDROP_CLIENT_DIR=$PWD
operator/launch-qubic3.sh
```

The launcher mounts the checkout at `/workspace/aqdrop-client`, mounts the
calibration data read-only at `/opt/qpus_calib`, and passes only the API host,
SFAPI token, and calibration path required by the runtime.

Inside the container, verify API access without dispatching a job:

```bash
aqdrop queue_list
aqdrop job_list
```

Run the daemon after selecting any optional filters:

```bash
aqdrop-operator --owner <nersc-username> --idRange any any
```

Run a single job in dry-run mode before allowing hardware execution:

```bash
aqdrop-run-qpu --id <job-id>
aqdrop-run-qpu --id <job-id> --execJob
```

Exit the shell when the operator session is complete. Refresh
`NERSC_OIDC_TOKEN` before it expires and restart the container with the new
token.
