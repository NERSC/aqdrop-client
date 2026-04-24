# AQDrop End-User Setup

This guide shows how to set up AQDrop as an end user, submit a minimal Qiskit
job, and retrieve the job record after it has been executed by a privileged
operator. AQDrop is a human-operated API on both ends of the service.

![AQDrop user setup diagram](AQDrop-user.png)

## Prerequisites

Ask the AQDrop service administrator for:

- your AQDrop username
- your AQDrop password
- the AQDrop API hostname

You will receive these values from the AQDrop administrator. The AQDrop Python
client reads credentials from these environment variables:

```bash
export AQDROP_USERNAME=<your-user-name>
export AQDROP_PASSWORD=<your-password>
export AQDROP_HOSTNAME=https://<aqdrop-api-host>
```

> **Credential safety**
>
> - **Keep credentials out of GitHub and out of container images.**
> - **Do not bake credentials into the image.**

Prefer storing credentials in your personal `.ssh` directory and sourcing them
at the start of each session.

For example, create `~/.ssh/aqdrop.creds` with these three variables.
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

If you need to build the image yourself:

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

Adapt that script for your account, paths, image tag, and credential source.
The launcher should pass `AQDROP_USERNAME`, `AQDROP_PASSWORD`, and
`AQDROP_HOSTNAME` into the container.

## Minimal Example for Submit and Retrieve Quantum Job on AQT QPU Named X6Y3

From the repository example directory:

```bash
cd AQDrop/examples
```

Submit a Bell-state job:

```bash
python3 job_submit_bell.py -q X6Y3
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
python3 job_retrieve.py --id 123 -v 2
python3 job_retrieve.py --id 123 -v 3
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

`examples/job_submit_bell.py` submits immediately. The larger
`examples/job_submit.py` script prepares a multi-circuit example and only
submits when `-E` is provided:

```bash
python3 job_submit.py -q <queue-name>
python3 job_submit.py -q <queue-name> -E
```
