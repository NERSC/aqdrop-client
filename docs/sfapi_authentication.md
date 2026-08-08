# SFAPI Authentication Setup

AQDrop authenticates clients with a NERSC Superfacility API (SFAPI) access
token. Create an SFAPI OAuth client once in Iris, then use the AQDrop helper to
generate a short-lived token whenever you start a client or operator session.

AQDrop does not issue credentials and does not support a separate AQDrop
username/password login. The API derives the NERSC username from the validated
SFAPI token and authorizes it through NERSC LDAP.

## Create an SFAPI Client in Iris

1. Sign in to the [NERSC Iris profile page](https://iris.nersc.gov/profile).
2. Find **Superfacility API Clients** and select **+ New Client**.
3. Create the client for your NERSC user account or an accessible collaboration
   account.
4. Select the **Green** client security level. Green is sufficient for AQDrop;
   a Yellow or Red client does not grant additional AQDrop permissions.
5. Add a source IP range for every environment where the client credentials
   will be used. Iris provides presets including **Your IP**, **Spin**, **DTN
   Nodes**, and **Perlmutter Login Nodes**. Choose the preset matching where you
   will generate and use the token.
6. Create the client and save its client ID and PEM-formatted private key.

Iris shows the private key only when the client is created. Store it like an SSH
private key: outside the repository, never in a container image, and readable
only by your account. On a shared NERSC system, set its mode to `400`:

```bash
mkdir -p "$HOME/.ssh"
install -m 400 <downloaded-private-key.pem> \
  "$HOME/.ssh/aqdrop-sfapi-private-key.pem"
printf '%s\n' '<sfapi-client-id>' > \
  "$HOME/.ssh/aqdrop-sfapi-client-id"
chmod 600 "$HOME/.ssh/aqdrop-sfapi-client-id"
```

The client remains usable until its configured expiration or until it is
deleted in Iris. The access tokens generated from it are short-lived, so obtain
a new token for each session and refresh it when it expires. See the
[NERSC SFAPI authentication documentation](https://docs.nersc.gov/services/sfapi/authentication/#client)
for the current client-lifetime and source-IP rules.

## Generate `SFAPI_TOKEN`

Install the AQDrop package first. The installation includes the
`aqdrop-generate-sfapi-token` command and its Authlib dependency.

Generate a token from the two files saved above and export it without printing
the credential to the terminal:

```bash
export SFAPI_TOKEN="$(aqdrop-generate-sfapi-token \
  --client-id-file "$HOME/.ssh/aqdrop-sfapi-client-id" \
  --private-key-file "$HOME/.ssh/aqdrop-sfapi-private-key.pem")"
export AQDROP_HOSTNAME=https://<aqdrop-api-host>
```

The helper exchanges a signed client assertion at the NERSC OIDC token
endpoint and writes only the access token to standard output. It does not
modify either credential file or persist the token. Confirm the configuration
with a read-only request:

```bash
aqdrop queue_list
```

Reuse the exported `SFAPI_TOKEN` for repeated commands until it expires. This
avoids an unnecessary client-credential exchange for each API call and is the
preferred mode when each command starts a new disposable container.

Run `aqdrop-generate-sfapi-token --help` to see all options. The optional
`--token-url` argument is intended for testing; normal NERSC use should keep the
default `https://oidc.nersc.gov/c2id/token` endpoint.

## Automatic Token Fetch

Instead of exporting a token explicitly, the CLI and Python SDK can fetch one
from environment variables. `SFAPI_CLIENT_ID` contains the client ID itself,
whereas `SFAPI_PRIVATE_KEY_PATH` contains a path:

```bash
export SFAPI_CLIENT_ID="$(<"$HOME/.ssh/aqdrop-sfapi-client-id")"
export SFAPI_PRIVATE_KEY_PATH="$HOME/.ssh/aqdrop-sfapi-private-key.pem"
export AQDROP_HOSTNAME=https://<aqdrop-api-host>

aqdrop queue_list
```

The private-key flow automatically caches an exchanged token in a
permission-restricted file under `/tmp/aqdrop-<uid>/`. Before exchanging the
credentials, the client checks the cached JWT and reuses it when its `exp`
claim is still valid. A `401` response invalidates the cached token; the client
then obtains a new token with the private key and retries the API request once.
Explicit `SFAPI_TOKEN` authentication is never refreshed automatically.

For container use, generate `SFAPI_TOKEN` on the host and pass it at runtime,
or mount the private key read-only and set `SFAPI_PRIVATE_KEY_PATH` to the
mounted location. A container removed after each command also removes its token
cache, so explicit `SFAPI_TOKEN` reuse is more efficient in that workflow.
Never bake the client ID, private key, or token into an image.
