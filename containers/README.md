# AQDrop Client Container

Build the client image from the repository root:

```bash
podman-hpc build \
  -f containers/aqdrop-client.dockerfile \
  -t aqdrop-client:latest .
podman-hpc migrate aqdrop-client:latest
```

The image entry point is `aqdrop`. Generate `SFAPI_TOKEN` on the host and pass
it with `AQDROP_HOSTNAME` at runtime. Do not put an SFAPI token, client ID, or
private key in the image.

`launch-perlmutter-example.sh` and `launch-workstation-example.sh` are
site-specific interactive launcher examples. Review and replace their account,
mount, and credential-file paths before use.
