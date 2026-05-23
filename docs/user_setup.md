# AQDrop End-User Setup

This guide shows how to set up AQDrop as an end user, submit a minimal Qiskit
job, and retrieve the job record after it has been executed by a privileged
operator. AQDrop is a human-operated API on both ends of the service.

![AQDrop user setup diagram](AQDrop-user.png)

## Prerequisites

Ask the AQDrop service administrator for:

- your AQDrop username
- either a valid NERSC OIDC bearer token
- or an SFAPI client ID plus the matching private key file
- the AQDrop API hostname

You will receive these values from the AQDrop administrator. The AQDrop Python
client can authenticate in either of these ways.

Direct token:

```bash
export AQDROP_USERNAME=<your-user-name>
export NERSC_OIDC_TOKEN=<your-nersc-token>
export AQDROP_HOSTNAME=https://<aqdrop-api-host>
```

SFAPI token fetch from client credentials:

```bash
export AQDROP_USERNAME=<your-user-name>
export AQDROP_CLIENT_ID=<your-sfapi-client-id>
export AQDROP_PRIVATE_KEY_PATH=$HOME/.ssh/aqdrop-sfapi-private-key.pem
export AQDROP_HOSTNAME=https://<aqdrop-api-host>
```

The SDK also accepts `token=...` directly, or `client_id=...` together with
`private_key_path=...` when you construct `aqdrop.AqdropClient(...)`.

Programmatic examples:

```python
import aqdrop

client = aqdrop.AqdropClient(token="<nersc-oidc-token>")
```

```python
import aqdrop

client = aqdrop.AqdropClient(
    client_id="<sfapi-client-id>",
    private_key_path="/path/to/private-key.pem",
)
```

In the SFAPI case, the private key should live in a user-private file outside
the repository, not in source control and not embedded in a container image.

> **Credential safety**
>
> - **Keep credentials out of GitHub and out of container images.**
> - **Do not bake credentials into the image.**

Prefer storing credentials in your personal `.ssh` directory and sourcing them
at the start of each session.

For example, create `~/.ssh/aqdrop.creds` with either the direct token form or
the SFAPI client-credentials form shown above.
Restrict access to the file:

```bash
chmod 600 ~/.ssh/aqdrop.creds
```

Source it when starting an AQDrop session:

```bash
source ~/.ssh/aqdrop.creds
```

For container use, source the credentials on the host and pass the environment
variables into the container at runtime. Inspect `examples/pm_balewski.src` to
see how to source credentials before the image is launched and pass the
environment variables to the image at execution time.

If you use the SFAPI client-credential flow inside a container, mount the
private-key file into the container and pass its mounted path through
`AQDROP_PRIVATE_KEY_PATH`.

## Laptop Setup

Install the AQDrop client:

```bash
pip install aqdrop
```

The example scripts in this repository submit Qiskit circuits, so install the
Qiskit-enabled package when you want to run those examples:

```bash
pip install "aqdrop[qiskit]"
```

If you want to use the repository examples directly:

```bash
git clone git@github.com:balewski/AQDrop.git
cd AQDrop/examples
```

## Perlmutter Podman-HPC Setup

On Perlmutter, a ready AQDrop Podman-HPC image may already be available:

```bash
podman-hpc images | grep aqdrop
```

If you need to build the image yourself you can modiffy the one provided:

```bash
git clone git@github.com:balewski/AQDrop.git
cd AQDrop/examples

podman-hpc build -f ubu24-aqdrop-x86.dockerfile -t ubu24-aqdrop:p2
podman-hpc migrate ubu24-aqdrop:p2
```

Start the container with the site-provided launcher script. For example, this
repository includes `pm_balewski.src` as a user-specific launcher:

```bash
. ./pm_balewski.src
```

Adapt that image starting script for your account, paths, image tag, and credential source.
The launcher should pass `AQDROP_USERNAME` and either `NERSC_OIDC_TOKEN` or
the pair `AQDROP_CLIENT_ID` / `AQDROP_PRIVATE_KEY_PATH`, plus
`AQDROP_HOSTNAME` into the container.

## Minimal Example for Submit and Retrieve Quantum Job on AQT QPU Named X6Y3

From the repository example directory:

```bash
cd AQDrop/examples
```

Submit a Bell-state job:

```bash
 ./job_submit_bell.py -q X6Y3
```

The submit script prints the assigned job ID, for example:

```text
Job submission successful; assigned job ID 123.
   ./job_retrieve.py --id 123
```

Retrieve the job record with that ID:

```bash
python3 job_retrieve.py --id 123
```

If the job is still queued, the retrieve script prints:

```text
no results available yet
```

Wait and run the same retrieve command again. Use higher verbosity to inspect
more detail:

```bash
 ./job_retrieve.py --id 123 -v 2
 ./job_retrieve.py --id 123 -v 3
```

`-v 2` prints the packed Qiskit circuits. `-v 3` prints the full returned job
record.

## Notes

Use the AQDrop CLI to inspect queues and jobs:

```bash
aqdrop queue_list
aqdrop job_list
```

`aqdrop queue_list` lists available queues. `aqdrop job_list` lists your jobs
and their status.

The CLI uses the same auth resolution as the Python SDK:

- `NERSC_OIDC_TOKEN` if you already have a bearer token
- otherwise `AQDROP_CLIENT_ID` plus `AQDROP_PRIVATE_KEY_PATH`

`examples/job_submit_bell.py` submits immediately. The larger
`examples/job_submit.py` script prepares a multi-circuit example and only
submits when `-E` is provided:

```bash
 ./job_submit.py -q <queue-name>
 ./job_submit.py -q <queue-name> -E
```
