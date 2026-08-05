# aqdrop CLI Reference

The `aqdrop` command line interface provides tools for managing jobs and queues within the AQDrop system.

## Authentication

The CLI uses the same auth configuration as `aqdrop.AqdropClient`.

Set `AQDROP_HOSTNAME` plus one of these auth options before running CLI
commands:

Existing SFAPI bearer token:

```bash
export AQDROP_HOSTNAME=https://<aqdrop-api-host>
export SFAPI_TOKEN=<your-sfapi-token>
```

This token is issued by NERSC outside AQDrop. AQDrop does not issue bearer
tokens, and the former AQDrop username/password `/token/` flow is not
supported.

Automatic SFAPI token fetch with client credentials:

```bash
export AQDROP_HOSTNAME=https://<aqdrop-api-host>
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
the private key file must contain the matching PEM key.

The server derives the username from the validated token and checks NERSC LDAP.
No separate AQDrop username is configured. The CLI action list reports the
required LDAP access; admin and operator privileges are independent.

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

### `job_decline`
Declines a queued job. Requires `aqdrop_operator`.

**Usage:**
`aqdrop job_decline --id <job_id> --output <message>`

**Arguments:**
- `--id`: The ID of the job.
- `--output`: The output message to associate with the job.

### `job_dump`
Retrieves and displays all metadata, input parameters, and output results for a specific job.

Regular users can dump their own jobs. Admins and operators can dump another
user's job after a live LDAP check.

**Usage:**
`aqdrop job_dump --id <job_id>`

**Arguments:**
- `--id`: The ID of the job.

### `job_reset`
Resets a job for another dispatch attempt. Requires `aqdrop_operator`.

**Usage:**
`aqdrop job_reset --id <job_id> [--message <reason>]`

**Arguments:**
- `--id`: The ID of the job.
- `--message`: An optional reset reason.

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
