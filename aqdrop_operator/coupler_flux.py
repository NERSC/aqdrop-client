"""Apply calibration-versioned coupler DC biases for one QPU job."""

import re
from pathlib import Path

import yaml


def load_coupler_flux(calib_dir):
    """Load the optional coupler-flux table beside a QPU config."""
    path = Path(calib_dir) / "coupler_flux.yaml"
    if not path.is_file():
        return {}

    with path.open(encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    return data.get("coupler_flux", {})


def apply_coupler_flux(config, active_qubits, coupler_flux):
    """Bias couplers touching active qubits and zero all other couplers."""
    if not coupler_flux:
        return {}

    active_qubits = set(active_qubits)
    applied = {}
    for channel in config["initialize"]:
        endpoints = {int(number) for number in re.findall(r"\d+", channel)}
        amplitude = coupler_flux.get(channel, 0.0) if endpoints & active_qubits else 0.0
        config[f"initialize/{channel}/amp"] = round(amplitude, 5)
        if amplitude:
            applied[channel] = amplitude
    return applied
