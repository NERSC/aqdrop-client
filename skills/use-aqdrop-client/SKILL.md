---
name: use-aqdrop-client
description: Use the AQDrop Python client and CLI safely. Use when an agent needs to authenticate with NERSC SFAPI, inspect queues or jobs, submit or retrieve a job, cancel a user job, administer queues with explicit approval, or troubleshoot client authentication, LDAP authorization, and API errors. Do not use for job execution, dispatch, QPU access, or operator daemon workflows; those belong to aqdrop-operator.
---

# Use AQDrop Client

Use the AQDrop SDK and CLI while protecting SFAPI credentials and preventing
unintended state changes. Read
[references/commands.md](references/commands.md) for command templates.

## Resolve The Environment

1. Confirm the API hostname. Use the user-provided target; never infer a
   production target from a development example.
2. Use a Python installation of `aqdrop` or the client image documented in the
   repository README.
3. Use `podman-hpc` at NERSC and the available Podman- or Docker-compatible
   runtime elsewhere.
4. Confirm SFAPI client ID and private-key paths only when token generation is
   needed. Do not assume credential paths without user confirmation.

## Authenticate Safely

Generate one short-lived `SFAPI_TOKEN` and reuse it for repeated calls.

- Never print, decode, log, commit, or return the token or private key.
- Never enable shell tracing while credentials are in scope.
- Do not place credentials in image layers or visible command arguments.
- Prefer host-side token generation for disposable containers.
- On `401`, refresh once. On `403`, report the required LDAP role instead of
  repeatedly authenticating.

## Execute Client Actions

1. Classify the action as read-only or state-changing.
2. Check current CLI arguments or the `AqdropClient` method signature.
3. Inspect the target queue or job before a mutation.
4. Run only the requested action.
5. Query the affected object after a mutation and report its final state.

Run queue and owned-job inspection directly when requested. Require explicit
intent before submitting or cancelling a job, creating a queue, or changing a
queue. Queue administration requires `aqdrop_admin` LDAP membership.

Use the SDK for submission because the CLI has no submission action. Read the
current `AqdropClient.submit_job` signature and an appropriate example before
constructing a payload.

## Keep Operator Work Separate

Do not execute or dispatch jobs, initialize QPU hardware, start an operator
daemon, or use operator-only reset/decline operations through this skill. Those
workflows are maintained in `NERSC/aqdrop-operator` and require separate
operator safeguards and live `aqdrop_operator` authorization.

## Report Results

Summarize the target API, installation or image, action, relevant queue/job ID,
and final state. Omit credentials and SSH banners.

Distinguish common failures:

- `401`: missing, expired, malformed, or source-IP-incompatible SFAPI token.
- `403`: identity lacks `aqdrop_users` or `aqdrop_admin` LDAP membership.
- `404`: requested queue or job does not exist or is not visible to the caller.
- `409`: requested state transition conflicts with the current resource state.
