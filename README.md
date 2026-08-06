# AQDrop

AQDrop is the management system for interaction with the Advanced Quantum Testbed (AQT) at NERSC. It provides a centralized API for authenticated job submission and role-based queue operation.

## User Documentation

User instructions are in [docs/](docs/). Start with
[docs/user_setup.md](docs/user_setup.md).

![AQDrop user setup diagram](docs/AQDrop-user.png)

Privileged operators should start with
[operator/README.md](operator/README.md). The operator runtime, container recipe,
and `qubic3` setup guide live in this repository because they consume the client
API and Qiskit job payloads; the API server repository contains only the service
and deployment assets.

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
    host="https://<aqdrop-api-host>",
    token="<sfapi-token>",
)
```

The existing token is issued by NERSC outside AQDrop. The retired AQDrop
username/password `/token/` flow is not supported.

Automatic SFAPI token fetch with client credentials:

```python
import aqdrop

client = aqdrop.AqdropClient(
    host="https://<aqdrop-api-host>",
    client_id="<sfapi-client-id>",
    private_key_path="/path/to/private-key.pem",
)
```

If you omit those constructor arguments, the SDK will look for environment
variables instead:

```bash
export AQDROP_HOSTNAME=https://<aqdrop-api-host>

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
