# AQDrop Command Reference

Use these templates after confirming the target environment. Read the repository's `docs/actions.md` and `operator/README.md` when command behavior may have changed.

## Container Session

At NERSC, set the published image and target API:

```bash
export AQDROP_IMAGE=registry.nersc.gov/dseg/aqdrop-operator:202608060
export AQDROP_HOSTNAME=https://aqdrop-api-dev2.lbl-b59.org
export SFAPI_CLIENT_ID_FILE="$HOME/.ssh/aqdrop-sfapi-client-id"
export SFAPI_PRIVATE_KEY_FILE="$HOME/.ssh/aqdrop-sfapi-private-key.pem"
```

Generate one token without displaying it:

```bash
export SFAPI_TOKEN="$(
  podman-hpc run --rm \
    --volume "$SFAPI_CLIENT_ID_FILE:/run/secrets/sfapi-client-id:ro" \
    --volume "$SFAPI_PRIVATE_KEY_FILE:/run/secrets/sfapi-private-key.pem:ro" \
    "$AQDROP_IMAGE" \
    aqdrop-generate-sfapi-token \
      --client-id-file /run/secrets/sfapi-client-id \
      --private-key-file /run/secrets/sfapi-private-key.pem
)"
test "${#SFAPI_TOKEN}" -gt 100
```

Run repeated commands with only the API host and token:

```bash
podman-hpc run --rm \
  -e AQDROP_HOSTNAME \
  -e SFAPI_TOKEN \
  "$AQDROP_IMAGE" aqdrop queue_list
```

For a remote Perlmutter login node, use the documented jump route, for example:

```bash
ssh -J perlmutter.nersc.gov login12
```

Do not include token values in agent output or shell tracing.

## Client Actions And Roles

| Action | LDAP access | State change |
|---|---|---|
| `aqdrop queue_list` | user or admin | No |
| `aqdrop job_list` | user for own; admin/operator for all | No |
| `aqdrop job_check --id ID` | user for own; admin/operator for any | No |
| `aqdrop job_dump --id ID` | user for own; admin/operator for any | No |
| `aqdrop job_cancel --id ID` | user for own; admin for any | Yes |
| `aqdrop job_reset --id ID` | operator | Yes |
| `aqdrop job_decline --id ID --output MESSAGE` | operator | Yes |
| `aqdrop queue_create ...` | admin | Yes |
| `aqdrop queue_update ...` | admin | Yes |

Admin and operator are independent roles. Membership in `aqdrop_admin` does not imply `aqdrop_operator`, or the reverse.

Useful read-only filters:

```bash
aqdrop job_list --id-min 1002 --id-max 1002
aqdrop job_list --status queued --max-jobs 20
aqdrop job_list --owner USERNAME
aqdrop queue_list --state open
```

Create the simulator queues expected by the Qiskit runner only when explicitly requested by an admin:

```bash
aqdrop queue_create \
  --queue ideal --type simu --limit LIMIT --max_qubits QUBITS \
  --description "Aer statevector simulator"

aqdrop queue_create \
  --queue noisy --type simu --limit LIMIT --max_qubits QUBITS \
  --description "Aer simulator using FakeTorino noise"
```

## Single-Job Operator Runs

Inspect a job before selecting a runner:

```bash
aqdrop job_check --id JOB_ID
aqdrop job_dump --id JOB_ID
```

Run the Qiskit path without dispatching results:

```bash
aqdrop-run-qiskit --id JOB_ID
```

Only after explicit execution approval and a successful dry run:

```bash
aqdrop-run-qiskit --id JOB_ID --execJob
```

The Qiskit mapping is currently fixed:

- `ideal`: Aer statevector simulator.
- `noisy`: Aer simulator configured from `FakeTorino`.

For a QPU run, mount the confirmed calibration tree and set its in-container path. Even without `--execJob`, the runner initializes a QPU connection.

```bash
podman-hpc run --rm \
  -e AQDROP_HOSTNAME \
  -e SFAPI_TOKEN \
  -e QUBIC_CALIB_BASE_PATH=/opt/qpus_calib \
  --volume "$QUBIC_CALIB_BASE_PATH:/opt/qpus_calib:ro" \
  "$AQDROP_IMAGE" aqdrop-run-qpu --id JOB_ID
```

Add `--execJob` only after explicit approval to execute on hardware and dispatch the result.

## Operator Daemon

The daemon executes and dispatches jobs; it has no dry-run mode. Bound its scope:

```bash
aqdrop-operator --owner USERNAME --idRange MIN_ID MAX_ID
```

Use `any` for one open range bound. Do not start an unbounded daemon unless the user explicitly requests continuous operation for all queued jobs.
