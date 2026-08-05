"""Utility functions for inspecting a qcal config.yaml."""

import ast

import yaml


def get_qubit_pairs(config_path: str) -> list:
    """Return the qubit pairs that have 2-qubit gates defined in the config.

    Args:
        config_path (str): path to config.yaml.

    Returns:
        list: list of (q0, q1) tuples, e.g. [(0,1), (1,2), ...].
    """
    with open(config_path) as f:
        config = yaml.safe_load(f)

    tq = config['two_qubit']
    pairs = []
    for pair_key in tq:
        pair = ast.literal_eval(str(pair_key))
        pairs.append(list(pair))

    return pairs
