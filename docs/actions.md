# aqdrop CLI Reference

The `aqdrop` command line interface provides a set of tools for managing jobs, members, and queues within the AQDrop system.

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

**Usage:**
`aqdrop job_list [args]`

**Arguments:**
- `--id-min`: Minimum job ID.
- `--id-max`: Maximum job ID.
- `--queue`: The name of the queue to list jobs for.
- `--user`: The username to list jobs for.
- `--status`: The job status to filter by.
- `--max-jobs`: Maximum number of jobs to return.
- `--created-min`: Filter jobs created after this time.
- `--created-max`: Filter jobs created before this time.
- `--reverse`: Reverse the order of results.

### `job_check`
Checks the current status of a specific job.

**Usage:**
`aqdrop job_check --id <job_id>`

**Arguments:**
- `--id`: The ID of the job.

### `job_cancel`
Cancels a pending or running job.

**Usage:**
`aqdrop job_cancel --id <job_id>`

**Arguments:**
- `--id`: The ID of the job.

### `job_decline`
Dispatches (completes) a job with a specific status and result message.

**Usage:**
`aqdrop job_decline --id <job_id> --status <status> --output <message>`

**Arguments:**
- `--id`: The ID of the job.
- `--status`: The status of the job (e.g., `success`, `failed`). Defaults to `success`.
- `--output`: The output message to associate with the job.

### `job_delete`
Permanently deletes a job record.

**Usage:**
`aqdrop job_delete --id <job_id>`

**Arguments:**
- `--id`: The ID of the job.

### `job_dump`
Retrieves and displays all metadata, input parameters, and output results for a specific job.

**Usage:**
`aqdrop job_dump --id <job_id>`

**Arguments:**
- `--id`: The ID of the job.

---

## Member Actions

### `member_create`
Creates a new user member in the system.

**Usage:**
`aqdrop member_create --name <username> [args]`

**Arguments:**
- `--name`: The username of the new member.
- `--email`: The email address of the new member.
- `--operator`: Set this flag to make the new user an operator.
- `--admin`: Set this flag to make the new user an admin.

This command outputs a shell snippet that can be redirected to a `.creds` file to set up the user's environment.

### `member_list`
Lists all members in the system.

**Usage:**
`aqdrop member_list [args]`

**Arguments:**
- `--skip`: The number of members to skip (offset). Defaults to 0.
- `--limit`: The maximum number of members to return.

### `member_permissions`
Updates the permissions and status of an existing member.

**Usage:**
`aqdrop member_permissions --name <username> [args]`

**Arguments:**
- `--name`: The username of the member.
- `--operator`: `true` or `false` to set operator status.
- `--admin`: `true` or `false` to set admin status.
- `--suspended`: `true` or `false` to suspend the user.

---

## Queue Actions

### `queue_create`
Creates a new job queue.

**Usage:**
`aqdrop queue_create --queue <queue_name> --type <type> --limit <limit> --max_qubits <qubits> [args]`

**Arguments:**
- `--queue`: The name of the queue.
- `--type`: The type of queue: `qpu` (quantum hardware) or `simu` (simulator).
- `--limit`: Max number of jobs any user can submit to this queue.
- `--max_qubits`: Maximum number of qubits available.
- `--default`: `true` or `false` to make the queue accessible to all users by default.
- `--description`: A description for the queue.

### `queue_list`
Lists available queues.

**Usage:**
`aqdrop queue_list [args]`

**Arguments:**
- `--state`: Filter by queue state (e.g., `open`, `down`).

### `queue_update`
Updates the configuration or state of an existing queue.

**Usage:**
`aqdrop queue_update --queue <queue_name> [args]`

**Arguments:**
- `--queue`: The name of the queue to update.
- `--new_name`: The new name for the queue.
- `--default`: `true` or `false` to change default access.
- `--limit`: Update the max number of jobs per user.
- `--state`: The new state of the queue (e.g., `open`, `down`).
