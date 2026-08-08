# AQDrop

AQDrop is the management system for interaction with the Advanced Quantum Testbed (AQT) at NERSC. It provides a centralized API for authenticated job submission and role-based queue operation.

## Quick Start on NERSC

This example uses the published operator image, which includes the `aqdrop`
client and its SFAPI token-fetching dependency. Before starting, obtain
`aqdrop_users` LDAP membership and create a Green SFAPI client with the
**Perlmutter Login Nodes** source-IP preset. Save the client ID and private key
as described in [SFAPI Authentication Setup](docs/sfapi_authentication.md).

Log in to the NERSC registry if necessary, then pull the image with
`podman-hpc`. See the
[NERSC registry login instructions](https://docs.nersc.gov/development/containers/registry/#login-to-the-registry)
for access requirements and login details:

```bash
export AQDROP_IMAGE=registry.nersc.gov/m4916/aqdrop-operator:202608060

podman-hpc login registry.nersc.gov
podman-hpc pull "$AQDROP_IMAGE"
```

Registry access requires authorization for the NERSC `m4916` project. Set the
production API and identify both credential files on the host:

```bash
export AQDROP_HOSTNAME=https://aqdrop-api.nersc.gov
export SFAPI_CLIENT_ID_FILE="$HOME/.ssh/aqdrop-sfapi-client-id"
export SFAPI_PRIVATE_KEY_FILE="$HOME/.ssh/aqdrop-sfapi-private-key.pem"
```

For repeated commands, exchange the private-key credentials once and keep the
short-lived token in the host environment. This avoids a token-endpoint request
for every disposable container:

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
```

Pass that token to the installed client in the image:

```bash
podman-hpc run --rm \
  -e AQDROP_HOSTNAME \
  -e SFAPI_TOKEN \
  "$AQDROP_IMAGE" aqdrop queue_list
```

A successful request prints the queues available from the deployed API. A
`401` response indicates rejected or expired SFAPI credentials; `403` means the
authenticated NERSC identity lacks the required AQDrop LDAP membership. The
same image also provides `aqdrop job_list` and the privileged operator commands.

## User Documentation

User instructions are in [docs/](docs/). Start with
[docs/user_setup.md](docs/user_setup.md).

![AQDrop user setup diagram](docs/AQDrop-user.png)

Privileged operators should start with
[operator/README.md](operator/README.md). The operator runtime, container recipe,
and `qubic3` setup guide live in this repository because they consume the client
API and Qiskit job payloads; the API server repository contains only the service
and deployment assets.

## Agent Skill

The repository includes the
[`use-aqdrop-tools`](skills/use-aqdrop-tools/SKILL.md) agent skill for operating
the client and operator tools. It covers secure SFAPI token reuse, LDAP role
requirements, queue and job actions, Qiskit and QPU dry runs, and safeguards for
state-changing dispatch commands.

The skill is not Codex-specific. Codex is used below as one installation
example, but the same skill directory can be used with other tools that support
agent skills, including Claude Code and OpenCode. Install it in the skill
directory configured for the selected tool; directory locations and invocation
syntax may differ between tools.

For Codex, install it from the repository root with:

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$CODEX_HOME/skills"
cp -R skills/use-aqdrop-tools "$CODEX_HOME/skills/"
```

Restart the agent tool after installation if required for skill discovery.
Codex may invoke the skill for matching AQDrop tasks, or invoke it explicitly
in a prompt as shown below. Use the corresponding invocation syntax in other
tools.

```text
Use $use-aqdrop-tools to list the queues on the AQDrop production API.
Use $use-aqdrop-tools to dry-run Qiskit job 1005 with the operator image.
```

The skill contains no credentials. Keep the SFAPI client ID and private key in
the external files described above and never add them to the repository.

## Library and Client

The `aqdrop` Python library provides a programmatic interface to the API, allowing users to interact with the quantum testbed via Python scripts.

The SDK supports either an existing NERSC SFAPI bearer token or automatic
SFAPI token fetch from a client ID plus a private-key file path.

The API validates the SFAPI token, derives the NERSC username from its `un:`
scope, and authorizes the identity using NERSC LDAP. The client does not send or
configure a separate AQDrop username. Access is managed outside AQDrop through
the `aqdrop_users`, `aqdrop_operator`, and `aqdrop_admin` LDAP groups.

### Client Authentication

Before using either authentication mode, create a **Green** SFAPI client in
NERSC Iris and securely save its client ID and private key. Green is sufficient
for AQDrop. The complete registration and token-helper workflow is in
[docs/sfapi_authentication.md](docs/sfapi_authentication.md).

The main client entry point is `aqdrop.AqdropClient`.

Existing SFAPI bearer token:

```python
import aqdrop

client = aqdrop.AqdropClient(
    host="https://aqdrop-api.nersc.gov",
    token="<sfapi-token>",
)
```

The existing token is issued by NERSC outside AQDrop. The retired AQDrop
username/password `/token/` flow is not supported.

Automatic SFAPI token fetch with client credentials:

```python
import aqdrop

client = aqdrop.AqdropClient(
    host="https://aqdrop-api.nersc.gov",
    client_id="<sfapi-client-id>",
    private_key_path="/path/to/private-key.pem",
)
```

If you omit those constructor arguments, the SDK will look for environment
variables instead:

```bash
export AQDROP_HOSTNAME=https://aqdrop-api.nersc.gov

# Option 1: existing SFAPI bearer token
export SFAPI_TOKEN=<your-sfapi-token>

# Option 2: automatic SFAPI token fetch
export SFAPI_CLIENT_ID=<your-sfapi-client-id>
export SFAPI_PRIVATE_KEY_PATH=$HOME/.ssh/aqdrop-sfapi-private-key.pem
```

To generate `SFAPI_TOKEN` explicitly from credentials stored in files:

```bash
export SFAPI_TOKEN="$(aqdrop-generate-sfapi-token \
  --client-id-file "$HOME/.ssh/aqdrop-sfapi-client-id" \
  --private-key-file "$HOME/.ssh/aqdrop-sfapi-private-key.pem")"
```

The helper prints only the token to standard output. It does not write the
token or private key to disk. See
[SFAPI Authentication Setup](docs/sfapi_authentication.md) for the Iris client
registration, source-IP selection, credential storage, and token refresh steps.

For repeated client commands, generating `SFAPI_TOKEN` once and passing it to
each command is more efficient than exchanging the client credentials for every
call. When the SDK is configured with `SFAPI_CLIENT_ID` and
`SFAPI_PRIVATE_KEY_PATH` instead, it caches an unexpired token in a private
temporary file and performs one fresh private-key exchange after a `401`.

### Installation

AQDrop requires Python 3.12 or newer. The client is installed from the NERSC
GitHub repository; do not use an unrelated package with the same name from a
package index.

Install the current `main` branch in a virtual environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "aqdrop @ git+https://github.com/NERSC/aqdrop-client.git@main"
aqdrop --help
```

For development or a version-controlled local install, clone the repository and
install from its root:

```bash
git clone https://github.com/NERSC/aqdrop-client.git
cd aqdrop-client
python -m pip install .
```

Use `python -m pip install ".[qiskit]"` for Qiskit submission support or
`python -m pip install ".[operator]"` for the operator runtime. The SFAPI token
flow dependency, `authlib`, is included in every installation.

At NERSC, `podman-hpc` is the supported container runtime and is used by default
throughout this documentation. When building or running the image elsewhere,
substitute the container build/runtime tool available in that environment, such
as `podman` or Docker.

### Authorization Roles

- `aqdrop_users` permits ordinary queue access and operations on the caller's jobs.
- `aqdrop_operator` permits job dispatch/reset and cross-user job inspection.
- `aqdrop_admin` permits queue administration, database reset, cross-user cancellation, and cross-user job inspection.

Admin and operator are independent roles. Accounts that require both sets of
privileges must belong to both LDAP groups.

### Operator Installation

Install the optional runtime dependencies directly from a client checkout:

```bash
python -m pip install ".[operator]"
```

This adds `aqdrop-operator`, `aqdrop-run-qiskit`, and `aqdrop-run-qpu`. Operator
actions still authenticate with the same SFAPI bearer token as ordinary client
requests and are authorized by live `aqdrop_operator` LDAP membership checks on
the API server.

The operator image installs both the `aqdrop` client CLI and operator commands
from the checkout used as its build context:

```bash
podman-hpc build \
  -f operator/containers/aqdrop-operator.dockerfile \
  -t aqdrop-operator:latest .
podman-hpc migrate aqdrop-operator:latest
podman-hpc run --rm aqdrop-operator:latest aqdrop
```

See [operator/README.md](operator/README.md) for authenticated client commands
and the complete operator workflow.
