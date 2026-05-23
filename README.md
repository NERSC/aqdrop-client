# AQDrop

AQDrop is the management system for interaction with the Advanced Quantum Testbed (AQT) at NERSC. It provides a centralized API for job submission, queue management, and member access control.

## User Documentation

User instructions are in [docs/](docs/). Start with
[docs/user_setup.md](docs/user_setup.md).

![AQDrop user setup diagram](docs/AQDrop-user.png)

## Library and Client

The `aqdrop` Python library provides a programmatic interface to the API, allowing users to interact with the quantum testbed via Python scripts.

The SDK supports either a directly supplied bearer token or SFAPI token fetch
from a client ID plus a private-key file path.

### Client Authentication

The main client entry point is `aqdrop.AqdropClient`.

Direct bearer token:

```python
import aqdrop

client = aqdrop.AqdropClient(
    host="https://<aqdrop-api-host>",
    token="<nersc-oidc-token>",
)
```

SFAPI client credentials:

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

# Option 1: direct token
export NERSC_OIDC_TOKEN=<your-token>

# Option 2: SFAPI client credentials
export AQDROP_CLIENT_ID=<your-sfapi-client-id>
export AQDROP_PRIVATE_KEY_PATH=$HOME/.ssh/aqdrop-sfapi-private-key.pem
```

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
