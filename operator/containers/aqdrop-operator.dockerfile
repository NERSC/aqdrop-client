FROM ubuntu:24.04

# Build from the aqdrop-client repository root. At NERSC use podman-hpc:
# podman-hpc build -f operator/containers/aqdrop-operator.dockerfile \
#   -t aqdrop-operator:latest .
# podman-hpc migrate aqdrop-operator:latest
# Outside NERSC, substitute the available container build tool.

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Los_Angeles \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Generic OS packages used by the interactive QPU environment.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        aptitude \
        autoconf \
        automake \
        build-essential \
        dnsutils \
        emacs \
        feh \
        g++ \
        gcc \
        git \
        graphviz \
        hdf5-tools \
        iputils-ping \
        locales \
        make \
        net-tools \
        openssh-server \
        plocate \
        python3-bitstring \
        python3-dev \
        python3-pip \
        python3-scipy \
        python3-tk \
        python3-venv \
        screen \
        ssh \
        sudo \
        tzdata \
        vim \
        wget \
        x11-apps \
        xterm && \
    rm -rf /var/lib/apt/lists/*

# Generic scientific Python packages used by qcal tooling.
RUN python3 -m venv "${VIRTUAL_ENV}" && \
    pip install --upgrade pip && \
    pip install \
        bitstring \
        h5py \
        jupyter \
        lmfit \
        matplotlib \
        "networkx[default]" \
        notebook \
        pandas \
        pytest \
        pytz \
        scikit-learn \
        scipy

# Install the client CLI and operator runtime from this checkout.
WORKDIR /opt/aqdrop-client
COPY pyproject.toml README.md license.txt ./
COPY aqdrop ./aqdrop
COPY aqdrop_operator ./aqdrop_operator
RUN python -m pip install --no-cache-dir ".[operator]" && \
    aqdrop --help >/dev/null

CMD ["/bin/bash"]
