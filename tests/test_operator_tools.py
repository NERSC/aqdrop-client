import argparse
import base64
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from aqdrop_operator import operator_daemon, qpy_utils


ROOT = Path(__file__).resolve().parents[1]


def test_operator_daemon_uses_owner_name_filter():
    parser = argparse.ArgumentParser()
    operator_daemon.add_args(parser)

    args = parser.parse_args(["--owner", "dingpf", "--idRange", "10", "20"])
    jobs = [
        {"id": 9, "owner_name": "dingpf"},
        {"id": 12, "owner_name": "other"},
        {"id": 15, "owner_name": "dingpf"},
        {"id": 21, "owner_name": "dingpf"},
    ]

    owner_jobs = operator_daemon._filter_jobs_by_owner(jobs, args.owner)
    filtered_jobs = operator_daemon._filter_jobs_by_id_range(
        owner_jobs, operator_daemon._parse_id_range(args.idRange)
    )

    assert filtered_jobs == [{"id": 15, "owner_name": "dingpf"}]


def test_qpy_codec_uses_base64_payload(monkeypatch):
    class FakeQpy:
        @staticmethod
        def dump(circuits, output):
            assert circuits == ["circuit"]
            output.write(b"qpy-data")

        @staticmethod
        def load(source):
            assert source.read() == b"qpy-data"
            return ["decoded-circuit"]

    monkeypatch.setitem(sys.modules, "qiskit", SimpleNamespace(qpy=FakeQpy))

    payload = qpy_utils.encode_circuits(["circuit"])

    assert payload == base64.b64encode(b"qpy-data").decode("ascii")
    assert qpy_utils.decode_circuits(payload) == ["decoded-circuit"]


def test_qpy_codec_rejects_invalid_base64():
    with pytest.raises(ValueError, match="valid base64 QPY"):
        qpy_utils.decode_circuits("not base64!")


def test_operator_image_installs_client_and_operator_package():
    dockerfile = (ROOT / "operator/containers/aqdrop-operator.dockerfile").read_text()

    assert 'python -m pip install --no-cache-dir ".[operator]"' in dockerfile
    assert "aqdrop --help" in dockerfile
    assert "COPY aqdrop ./aqdrop" in dockerfile
    assert "COPY aqdrop_operator ./aqdrop_operator" in dockerfile


def test_qiskit_operator_uses_current_get_job_signature():
    source = (ROOT / "aqdrop_operator/qiskit_operator.py").read_text()

    assert "self.client.get_job(job_id)" in source
    assert "extract_qpy" not in source


def test_operator_launcher_defaults_to_podman_hpc_without_source_mount():
    launcher = (ROOT / "operator/launch-qubic3.sh").read_text()

    assert "AQDROP_CONTAINER_RUNTIME=${AQDROP_CONTAINER_RUNTIME:-podman-hpc}" in launcher
    assert 'exec "$AQDROP_CONTAINER_RUNTIME" run' in launcher
    assert "AQDROP_CLIENT_DIR" not in launcher
    assert "/workspace/aqdrop-client" not in launcher
