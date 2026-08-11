FROM python:3.12-slim

# Build from the aqdrop-client repository root. At NERSC use podman-hpc:
# podman-hpc build -f containers/aqdrop-client.dockerfile \
#   -t aqdrop-client:latest .
# podman-hpc migrate aqdrop-client:latest
#
# Outside NERSC, substitute the available builder, for example:
# podman build -f containers/aqdrop-client.dockerfile \
#   -t aqdrop-client:latest .

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

RUN python -m venv "${VIRTUAL_ENV}" && \
    pip install --no-cache-dir --upgrade pip

# Install AQDrop from the checkout used as the build context.
WORKDIR /opt/aqdrop-client
COPY pyproject.toml README.md license.txt ./
COPY aqdrop ./aqdrop
RUN python -m pip install --no-cache-dir ".[qiskit]" && \
    aqdrop --help >/dev/null && \
    aqdrop-generate-sfapi-token --help >/dev/null

ENTRYPOINT ["aqdrop"]
