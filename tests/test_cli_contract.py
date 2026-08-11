import argparse
import importlib
import pkgutil

import aqdrop.actions
from aqdrop import defs
from aqdrop.actions import job_list, queue_list, queue_update


def test_cli_has_no_member_management_actions():
    action_names = {module.name for module in pkgutil.iter_modules(aqdrop.actions.__path__)}

    assert not {name for name in action_names if name.startswith("member_")}


def test_cli_has_no_operator_only_actions():
    action_names = {module.name for module in pkgutil.iter_modules(aqdrop.actions.__path__)}

    assert "job_reset" not in action_names
    assert "job_decline" not in action_names


def test_every_action_describes_ldap_access():
    for module_info in pkgutil.iter_modules(aqdrop.actions.__path__):
        module = importlib.import_module(f"aqdrop.actions.{module_info.name}")
        info = module.action_info()
        assert set(info) == {"access", "description"}
        assert info["access"]


def test_queue_list_accepts_current_server_states():
    parser = argparse.ArgumentParser()
    queue_list.add_args(parser)

    for state in defs.QueueState:
        assert parser.parse_args(["--state", state.value]).state == state.value


def test_job_list_uses_owner_name_vocabulary():
    parser = argparse.ArgumentParser()
    job_list.add_args(parser)

    args = parser.parse_args(["--owner", "other-user"])

    assert args.owner == "other-user"


def test_queue_update_accepts_current_server_fields():
    parser = argparse.ArgumentParser()
    queue_update.add_args(parser)

    args = parser.parse_args(
        ["--queue", "qpu", "--state", "closed", "--max-qubits", "16", "--type", "qpu"]
    )

    assert args.state == "closed"
    assert args.max_qubits == 16
    assert args.type == "qpu"
