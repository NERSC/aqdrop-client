---
name: use-aqdrop-tools
description: Operate AQDrop through its Python client CLI, SDK, and privileged operator commands. Use when Codex needs to authenticate with NERSC SFAPI, run AQDrop commands directly or through the published operator container, inspect or manage queues and jobs, test a Qiskit or QPU runner, start a bounded operator workflow, or troubleshoot AQDrop authentication, LDAP authorization, queue compatibility, and dispatch failures.
---

# Use AQDrop Tools

Use AQDrop client and operator commands while protecting SFAPI credentials and preventing unintended job or hardware execution. Read [references/commands.md](references/commands.md) for command templates and the role matrix.

## Resolve The Environment

1. Confirm the API hostname. Use the user-provided target; never infer a production target from a development example.
2. Prefer the published operator image when working at NERSC because it contains both client and operator commands. Use the image tag documented in the repository README.
3. Use `podman-hpc` at NERSC. Use the available Podman or Docker-compatible runtime elsewhere.
4. Confirm the SFAPI client ID and private-key file paths. At NERSC, expect the README defaults only when the user has confirmed them.
5. When a specific Perlmutter login node is required, connect through `perlmutter.nersc.gov` as the jump host.

## Authenticate Safely

Generate one short-lived `SFAPI_TOKEN` and reuse it for repeated disposable-container calls. Mount the client ID and private key read-only; pass only the token and API hostname to later containers.

- Never print, decode, log, commit, or return the token or private key.
- Never enable shell tracing while credentials are in scope.
- Do not place credentials in image layers or command-line arguments visible to other users.
- If direct private-key mode is used outside disposable containers, let the client reuse its permission-restricted temporary token cache.
- On `401`, refresh the SFAPI token once. On `403`, report the required LDAP role instead of repeatedly authenticating.

## Execute Client Actions

1. Classify the request as read-only, mutating, or operator execution.
2. Check the action and arguments with the current CLI or repository source; do not rely on stale syntax.
3. For mutations, inspect the target queue or job first and state the intended transition.
4. Run only the action the user requested.
5. For mutations, query the affected object afterward and report the resulting state.

Run read-only listing and inspection actions directly when requested. Require explicit user intent before creating or updating queues, cancelling or resetting jobs, declining jobs, dispatching results, or changing any server state.

Use the SDK for job submission because the current CLI does not provide a submission action. Read the current `AqdropClient.submit_job` signature and repository examples before constructing a payload.

## Execute Operator Actions

Inspect the job first. Confirm it is queued, identify its owner and queue, and verify that the queue matches the runner.

- Run `aqdrop-run-qiskit --id JOB_ID` without `--execJob` first. The current Qiskit runner accepts only simulator queues named `ideal` and `noisy`.
- Treat `--execJob` as a state-changing execution. Use it only when the user explicitly requests execution after reviewing dry-run output.
- Treat QPU dry runs as privileged hardware-environment operations because they load calibration data and initialize a QPU connection. Require the intended QPU host, queue, and calibration path.
- Never add `--execJob` merely to work around a dry-run failure.
- Treat `aqdrop-operator` as immediately mutating: it dispatches matching queued jobs with `execJob=True`. Start it only on explicit request and use the narrowest practical `--owner` and `--idRange` filters.
- Do not silently map an unsupported simulator queue to `ideal` or `noisy`. Report the mismatch and ask whether to create a supported queue or change the code.

## Report Results

Summarize the target API, image or installation used, command category, and outcome. Include relevant queue/job IDs and final states. Omit credentials and avoid reproducing SSH login banners.

Distinguish common failures:

- `401`: missing, expired, malformed, or source-IP-incompatible SFAPI token.
- `403`: authenticated identity lacks the required `aqdrop_users`, `aqdrop_operator`, or `aqdrop_admin` LDAP membership.
- Unsupported Qiskit queue: the job is not assigned to `ideal` or `noisy`.
- QPU setup failure: calibration path, active queue configuration, network access, or hardware environment is unavailable.
