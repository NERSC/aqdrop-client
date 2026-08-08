FROM ubuntu:24.04

# Build from the aqdrop-client repository root. At NERSC use podman-hpc:
# podman-hpc build -f examples/ubu24-aqdrop.dockerfile \
#   -t ubu24-aqdrop:latest .
# podman-hpc migrate ubu24-aqdrop:latest
#
# Outside NERSC, substitute the available builder, for example:
# podman build -f examples/ubu24-aqdrop.dockerfile \
#   -t ubu24-aqdrop:latest --platform linux/arm64 .

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Los_Angeles \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# --- generic OS ppackages ---
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

# -- generic python libs ---
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

# Install AQDrop from the checkout used as the build context.
WORKDIR /opt/aqdrop-client
COPY pyproject.toml README.md license.txt ./
COPY aqdrop ./aqdrop
COPY aqdrop_operator ./aqdrop_operator
RUN python -m pip install --no-cache-dir \
        ".[qiskit]" \
        qiskit-aer \
        qiskit-ibm-runtime && \
    aqdrop --help >/dev/null
CMD ["/bin/bash"]
