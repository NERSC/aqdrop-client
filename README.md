# AQDrop Client

AQDrop Client is the Python SDK and command-line interface for the AQDrop API.
It authenticates with NERSC Superfacility API (SFAPI) tokens and supports queue
inspection, job submission and retrieval, user job control, and authorized
queue administration.

Privileged job execution, QPU integration, and operator containers are
maintained separately in the private
[`NERSC/aqdrop-operator`](https://github.com/NERSC/aqdrop-operator) repository.

## Quick Start

AQDrop requires Python 3.12 or newer. On Perlmutter, load a current Python
module before creating the environment:

```bash
module load python
python -m venv "$HOME/.venvs/aqdrop-client"
. "$HOME/.venvs/aqdrop-client/bin/activate"
python -m pip install --upgrade pip
python -m pip install \
  "aqdrop @ git+https://github.com/NERSC/aqdrop-client.git@main"
```

Obtain `aqdrop_users` LDAP membership and create a Green SFAPI client with the
**Perlmutter Login Nodes** source-IP preset. Save the client ID and private key
as described in [SFAPI Authentication Setup](docs/sfapi_authentication.md).

Generate one token for the session and reuse it for subsequent commands:

```bash
export AQDROP_HOSTNAME=https://aqdrop-api.nersc.gov
export SFAPI_TOKEN="$(aqdrop-generate-sfapi-token \
  --client-id-file "$HOME/.ssh/aqdrop-sfapi-client-id" \
  --private-key-file "$HOME/.ssh/aqdrop-sfapi-private-key.pem")"

aqdrop queue_list
aqdrop job_list
```

A `401` response indicates rejected or expired SFAPI credentials. A `403`
response means the authenticated NERSC identity lacks the LDAP membership
required for that action.

## Installation

For a version-controlled local installation:

```bash
git clone https://github.com/NERSC/aqdrop-client.git
cd aqdrop-client
python -m pip install .
```

Install Qiskit support when using the circuit-submission examples:

```bash
python -m pip install ".[qiskit]"
```

The base installation provides:

- the `aqdrop` Python package
- the `aqdrop` CLI
- the `aqdrop-generate-sfapi-token` helper

It does not install an operator runtime or QPU dependencies.

## Container

At NERSC, `podman-hpc` is the supported container runtime. Build the client
image from the repository root:

```bash
podman-hpc build \
  -f containers/aqdrop-client.dockerfile \
  -t aqdrop-client:latest .
podman-hpc migrate aqdrop-client:latest
```

Outside NERSC, use the available container builder/runtime, such as Podman or
Docker. Generate the token on the host, then pass only the API hostname and
short-lived token to repeated containers:

```bash
podman-hpc run --rm \
  -e AQDROP_HOSTNAME \
  -e SFAPI_TOKEN \
  aqdrop-client:latest queue_list
```

The container entry point is `aqdrop`, so the argument above is the CLI action.
See [containers/README.md](containers/README.md) for the interactive launcher
examples and their site-specific path requirements.

## Authentication

The SDK supports either an existing NERSC SFAPI bearer token or automatic
token exchange from a client ID and private-key file. Green SFAPI clients are
sufficient because AQDrop authorization comes from LDAP membership.

Existing token:

```python
import aqdrop

client = aqdrop.AqdropClient(
    host="https://aqdrop-api.nersc.gov",
    token="<sfapi-token>",
)
```

Automatic token exchange:

```python
import aqdrop

client = aqdrop.AqdropClient(
    host="https://aqdrop-api.nersc.gov",
    client_id="<sfapi-client-id>",
    private_key_path="/path/to/private-key.pem",
)
```

Equivalent environment configuration:

```bash
export AQDROP_HOSTNAME=https://aqdrop-api.nersc.gov

# Option 1: existing token
export SFAPI_TOKEN=<your-sfapi-token>

# Option 2: client credentials
export SFAPI_CLIENT_ID=<your-sfapi-client-id>
export SFAPI_PRIVATE_KEY_PATH=$HOME/.ssh/aqdrop-sfapi-private-key.pem
```

For repeated use, explicitly generating `SFAPI_TOKEN` once is more efficient
than exchanging client credentials for every command. When configured with a
client ID and private-key path, the SDK caches an unexpired token in a
permission-restricted temporary file and refreshes it once after a `401`.

See [docs/sfapi_authentication.md](docs/sfapi_authentication.md) for Iris
registration, source-IP selection, credential storage, and token refresh.

## SDK And CLI

The main Python entry point is `aqdrop.AqdropClient`. The examples under
[`examples/`](examples/) demonstrate Qiskit job submission and retrieval.

The CLI uses an action-based interface:

```bash
aqdrop
aqdrop queue_list --state open
aqdrop job_list --status queued --max-jobs 20
aqdrop job_check --id JOB_ID
aqdrop job_cancel --id JOB_ID
```

Administrative queue actions require `aqdrop_admin` LDAP membership. Ordinary
users can operate only on their own jobs. See the
[CLI reference](docs/actions.md) for the complete action and role matrix.

## Documentation

- [End-user setup](docs/user_setup.md)
- [SFAPI authentication](docs/sfapi_authentication.md)
- [CLI actions](docs/actions.md)
- [Examples](examples/)

## Agent Skill

The repository includes the client-focused
[`use-aqdrop-client`](skills/use-aqdrop-client/SKILL.md) skill. It covers safe
SFAPI token reuse, read-only inspection, user job operations, queue
administration, and verification after state changes.

The skill is not Codex-specific. It can be used with Codex, Claude Code,
OpenCode, and other tools that support agent skills. For Codex:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$CODEX_HOME/skills"
cp -R skills/use-aqdrop-client "$CODEX_HOME/skills/"
```

Example invocation:

```text
Use $use-aqdrop-client to list queues on the AQDrop production API.
```

The skill contains no credentials. Keep SFAPI credentials outside the
repository and container image.
