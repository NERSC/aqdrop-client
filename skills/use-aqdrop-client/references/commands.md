# AQDrop Client Command Reference

Confirm the API target before using these templates.

## Authentication

```bash
export AQDROP_HOSTNAME=https://aqdrop-api.nersc.gov
export SFAPI_CLIENT_ID_FILE="$HOME/.ssh/aqdrop-sfapi-client-id"
export SFAPI_PRIVATE_KEY_FILE="$HOME/.ssh/aqdrop-sfapi-private-key.pem"

export SFAPI_TOKEN="$(aqdrop-generate-sfapi-token \
  --client-id-file "$SFAPI_CLIENT_ID_FILE" \
  --private-key-file "$SFAPI_PRIVATE_KEY_FILE")"
test "${#SFAPI_TOKEN}" -gt 100
```

Do not display the token or enable shell tracing.

## Read-Only Actions

```bash
aqdrop queue_list
aqdrop queue_list --state open
aqdrop job_list --max-jobs 20
aqdrop job_list --status queued --max-jobs 20
aqdrop job_check --id JOB_ID
aqdrop job_dump --id JOB_ID
```

Ordinary users can inspect only their own jobs. Cross-user inspection requires
a role authorized by the API.

## User Job Control

Inspect the job before cancellation:

```bash
aqdrop job_check --id JOB_ID
aqdrop job_cancel --id JOB_ID
aqdrop job_check --id JOB_ID
```

The current CLI does not submit jobs. Use `AqdropClient.submit_job` and the
repository examples for Qiskit payload construction.

## Queue Administration

These commands require `aqdrop_admin` LDAP membership and explicit approval:

```bash
aqdrop queue_create \
  --queue QUEUE --type simu --limit LIMIT --max_qubits QUBITS \
  --description "DESCRIPTION"

aqdrop queue_update --queue QUEUE --state closed
aqdrop queue_list
```

Inspect the queue before changing it and list queues again afterward.

## Client Container

Build from the repository root:

```bash
podman-hpc build \
  -f containers/aqdrop-client.dockerfile \
  -t aqdrop-client:latest .
podman-hpc migrate aqdrop-client:latest
```

The image entry point is `aqdrop`:

```bash
podman-hpc run --rm \
  -e AQDROP_HOSTNAME \
  -e SFAPI_TOKEN \
  aqdrop-client:latest queue_list
```

Job execution, result dispatch, QPU access, and operator daemon operation are
out of scope for this client skill.
