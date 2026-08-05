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
token or private key to disk.

### Installation

The following command will install the AQDrop library, but will not install Qiskit.
```bash
pip install aqdrop
```

In order to submit Qiskit circuits, install Qiskit manually or include Qiskit in your AQDrop install (ensuring version compatibility) with the following command:
```bash
pip install aqdrop[qiskit]
```

The SFAPI token flow uses `authlib`, which is included in the package
dependencies.

### Authorization Roles

- `aqdrop_users` permits ordinary queue access and operations on the caller's jobs.
- `aqdrop_operator` permits job dispatch/reset and cross-user job inspection.
- `aqdrop_admin` permits queue administration, database reset, cross-user cancellation, and cross-user job inspection.

Admin and operator are independent roles. Accounts that require both sets of
privileges must belong to both LDAP groups.

### Operator Installation

Install the optional runtime dependencies from a client checkout:

```bash
pip install ".[operator]"
```

This adds `aqdrop-operator`, `aqdrop-run-qiskit`, and `aqdrop-run-qpu`. Operator
actions still authenticate with the same SFAPI bearer token as ordinary client
requests and are authorized by live `aqdrop_operator` LDAP membership checks on
the API server.
