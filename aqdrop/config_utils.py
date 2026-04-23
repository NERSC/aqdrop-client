"""Utility functions for inspecting a qcal config.yaml."""

import ast
import yaml

# Maps qcal gate names (as they appear in config) to Qiskit basis gate names.
_GATE_MAP = {
    'X90':  'rx',
    'CZ':   'cz',
    'CNOT': 'cx',
    'CX':   'cx',
    'iSWAP': 'iswap',
}


def get_basis_gates(config_path: str) -> list:
    """Return the Qiskit-style basis gates supported by the hardware config.

    Mapping rules:
      single_qubit X90     --> 'rx'
      VirtualZ (via X90)   --> 'rz'  (always present when X90 exists)
      two_qubit  CZ        --> 'cz'

    Args:
        config_path (str): path to config.yaml.

    Returns:
        list: Qiskit basis gate names, e.g. ['rx', 'rz', 'cz'].
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)

    basis_gates = []

    # --- Single-qubit gates ---
    sq = config.get('single_qubit', {})
    if sq:
        first_qubit = next(iter(sq.values()), {})
        ge = first_qubit.get('GE', {})
        if 'X90' in ge:
            basis_gates.append('rx')
            basis_gates.append('rz')  # VirtualZ is always paired with X90

    # --- Two-qubit gates ---
    tq = config.get('two_qubit', {})
    for gates in tq.values():
        for gate_name in gates:
            qiskit_name = _GATE_MAP.get(gate_name, gate_name.lower())
            if qiskit_name not in basis_gates:
                basis_gates.append(qiskit_name)

    return basis_gates


def get_qubit_pairs(config_path: str) -> list:
    """Return the qubit pairs that have 2-qubit gates defined in the config.

    Args:
        config_path (str): path to config.yaml.

    Returns:
        list: list of (q0, q1) tuples, e.g. [(0,1), (1,2), ...].
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)

    tq = config.get('two_qubit', {})
    pairs = []
    for pair_key in tq:
        pair = ast.literal_eval(str(pair_key))
        pairs.append(pair)

    return pairs



# if __name__ == '__main__':
#     import sys

#     config_path = sys.argv[1] if len(sys.argv) > 1 else 'configs/config.yaml'

#     print('Basis gates:', get_basis_gates(config_path))
#     print('Qubit pairs:', get_qubit_pairs(config_path))
