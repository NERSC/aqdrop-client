import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _project_metadata():
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["project"]


def test_operator_runtime_is_not_in_client_repository():
    assert not (ROOT / "aqdrop_operator").exists()
    assert not (ROOT / "operator").exists()


def test_client_distribution_has_no_operator_entry_points_or_extra():
    project = _project_metadata()

    assert set(project["scripts"]) == {
        "aqdrop",
        "aqdrop-generate-sfapi-token",
    }
    assert "operator" not in project["optional-dependencies"]


def test_base_requirements_do_not_install_quantum_runtimes():
    requirements = (ROOT / "requirements.txt").read_text()

    assert "qiskit" not in requirements
    assert "quantum-calibration" not in requirements
    assert "lbl-qubic" not in requirements


def test_client_container_contains_only_client_package():
    dockerfile = (ROOT / "containers/aqdrop-client.dockerfile").read_text()

    assert dockerfile.startswith("FROM python:3.12-slim")
    assert "COPY aqdrop ./aqdrop" in dockerfile
    assert "COPY aqdrop_operator" not in dockerfile
    assert '".[qiskit]"' in dockerfile
    assert 'ENTRYPOINT ["aqdrop"]' in dockerfile
    assert "qiskit-aer" not in dockerfile
    assert "qiskit-ibm-runtime" not in dockerfile


def test_client_skill_has_client_only_identity():
    skill = (ROOT / "skills/use-aqdrop-client/SKILL.md").read_text()

    assert "name: use-aqdrop-client" in skill
    assert "aqdrop-run-qiskit" not in skill
    assert "aqdrop-run-qpu" not in skill
    assert "aqdrop-operator --" not in skill
