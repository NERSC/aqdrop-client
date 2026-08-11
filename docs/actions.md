# aqdrop CLI Reference

The `aqdrop` command line interface provides tools for managing jobs and queues within the AQDrop system.

## Installation

AQDrop requires Python 3.12 or newer. Install the client from the NERSC GitHub
repository before using these commands:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install "aqdrop @ git+https://github.com/NERSC/aqdrop-client.git@main"
aqdrop --help
```

For a local checkout or the Qiskit extra, follow
[End-User Setup](user_setup.md#install-the-client).

## Authentication

The CLI uses the same auth configuration as `aqdrop.AqdropClient`.

Create a **Green** SFAPI client in NERSC Iris before configuring the CLI; Green
is sufficient for AQDrop. Follow [SFAPI Authentication
Setup](sfapi_authentication.md) for client registration, source-IP selection,
secure key storage, and the complete token-helper workflow.

Set `AQDROP_HOSTNAME` plus one of these auth options before running CLI
commands:

Existing SFAPI bearer token:

```bash
export AQDROP_HOSTNAME=https://aqdrop-api.nersc.gov
export SFAPI_TOKEN=<your-sfapi-token>
```

This token is issued by NERSC outside AQDrop. AQDrop does not issue bearer
tokens, and the former AQDrop username/password `/token/` flow is not
supported.

Automatic SFAPI token fetch with client credentials:

```bash
export AQDROP_HOSTNAME=https://aqdrop-api.nersc.gov
export SFAPI_CLIENT_ID=<your-sfapi-client-id>
export SFAPI_PRIVATE_KEY_PATH=$HOME/.ssh/aqdrop-sfapi-private-key.pem
```

To populate `SFAPI_TOKEN` from credentials stored in files:

```bash
export SFAPI_TOKEN="$(aqdrop-generate-sfapi-token \
  --client-id-file "$HOME/.ssh/aqdrop-sfapi-client-id" \
  --private-key-file "$HOME/.ssh/aqdrop-sfapi-private-key.pem")"
```

The helper prints only the token. The client ID file must contain one value;
the private key file must contain the matching PEM key. SFAPI access tokens are
short-lived, so rerun the helper when the token expires. For repeated commands,
reuse `SFAPI_TOKEN` until then instead of exchanging the credentials for each
call.

When the CLI uses `SFAPI_CLIENT_ID` and `SFAPI_PRIVATE_KEY_PATH`, it caches the
exchanged token in a user-only temporary file and reuses it while unexpired. If
the API returns `401`, the CLI invalidates that cache, fetches a new token with
the private key, and retries once. Explicit `SFAPI_TOKEN` values are not
automatically refreshed.

The server derives the username from the validated token and checks NERSC LDAP.
No separate AQDrop username is configured. The CLI action list reports the
required LDAP access. Operator execution commands are maintained in the
separate `NERSC/aqdrop-operator` repository.

## General Usage

The CLI follows a simple action-based pattern:

```bash
aqdrop <action> [args...]
```

To see a list of all available actions, run:
```bash
aqdrop
```

For detailed help on a specific action, use the `--help` flag:
```bash
aqdrop <action> --help
```

---

## Job Actions

### `job_list`
Lists jobs matching the specified filters.

Regular users can list only their own jobs. Members of `aqdrop_admin` or
`aqdrop_operator` can perform cross-user and global queries after a live LDAP
check.

**Usage:**
`aqdrop job_list [args]`

**Arguments:**
- `--id-min`: Minimum job ID.
- `--id-max`: Maximum job ID.
- `--queue`: The name of the queue to list jobs for.
- `--owner`: The owner username to list jobs for. Requires admin or operator access when it differs from the caller.
- `--status`: The job status to filter by.
- `--max-jobs`: Maximum number of jobs to return.
- `--created-min`: Filter jobs created after this time.
- `--created-max`: Filter jobs created before this time.
- `--reverse`: Reverse the order of results.

### `job_check`
Checks the current status of a specific job.

Regular users can check their own jobs. Admins and operators can check another
user's job after a live LDAP check.

**Usage:**
`aqdrop job_check --id <job_id>`

**Arguments:**
- `--id`: The ID of the job.

### `job_cancel`
Cancels a pending or running job.

Regular users can cancel their own jobs. Only admins can cancel another user's
job.

**Usage:**
`aqdrop job_cancel --id <job_id>`

**Arguments:**
- `--id`: The ID of the job.

### `job_dump`
Retrieves and displays all metadata, input parameters, and output results for a specific job.

Regular users can dump their own jobs. Admins and operators can dump another
user's job after a live LDAP check.

**Usage:**
`aqdrop job_dump --id <job_id>`

**Arguments:**
- `--id`: The ID of the job.

---

## Queue Actions

### `queue_create`
Creates a new job queue.

Requires `aqdrop_admin`.

**Usage:**
`aqdrop queue_create --queue <queue_name> --type <type> --limit <limit> --max_qubits <qubits> [args]`

**Arguments:**
- `--queue`: The name of the queue.
- `--type`: The type of queue: `qpu` (quantum hardware) or `simu` (simulator).
- `--limit`: Max number of jobs any user can submit to this queue.
- `--max_qubits`: Maximum number of qubits available.
- `--description`: A description for the queue.

### `queue_list`
Lists available queues.

Requires ordinary AQDrop access through `aqdrop_users` or `aqdrop_admin`.

**Usage:**
`aqdrop queue_list [args]`

**Arguments:**
- `--state`: Filter by queue state: `open`, `closed`, or `retired`.

### `queue_update`
Updates the configuration or state of an existing queue.

Requires `aqdrop_admin`.

**Usage:**
`aqdrop queue_update --queue <queue_name> [args]`

**Arguments:**
- `--queue`: The name of the queue to update.
- `--limit`: Update the max number of jobs per user.
- `--state`: The new state: `open`, `closed`, or `retired`.
- `--max-qubits`: Update the maximum qubit count.
- `--type`: Update the queue type to `qpu` or `simu`.
