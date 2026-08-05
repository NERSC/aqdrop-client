import argparse
import base64
import sys
from types import SimpleNamespace

import pytest

from aqdrop_operator import operator_daemon, qpy_utils


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
