"""Per-job coupler DC biasing for chips that need it (IQM20Q).

Moved out of temp_rpe.py so both the RPE demo and the operator test harness
(test_qpu.py) share one copy.  In AQDrop this belongs in
AQDrop_dev/operator/ next to AqdropOperator.py, called from qpu_connect().

The calibrated table lives in the chip's calibration directory as
coupler_flux.yaml, next to config.yaml -- versioned with the same calib_tag.
Chips without the file (X6Y3) skip the whole mechanism: load returns {} and
apply becomes a no-op.
"""

import os
import re

import yaml


def load_coupler_flux(calib_dir):
    """Read the calibrated coupler table from the chip's calib directory.

    Args:
        calib_dir: the chip's calibration directory (the one holding
            config.yaml).  Looks for coupler_flux.yaml by presence; absent
            file means the chip has no coupler DC and returns {}.

    Three places this could have lived, and why it is here:

      active_qpus.yaml -- no.  That is AQDrop's routing index: which chip a
        queue points at, its calib_tag, ip and port.  Per queue, ~3 lines,
        changes when a queue is repointed or a board moves.  Coupler amps are
        not routing, they change on every recalibration, and one chip may back
        several queues -- the table would be duplicated per queue.

      config.yaml initialize/ -- no.  That section is runtime state: which
        couplers are hot right now.  Parking the full table there means the
        file's resting state is "every coupler energised", so anyone opening
        it in a notebook and driving qcal directly gets all 30 hot.  That is
        exactly the failure this whole mechanism exists to prevent.

      coupler_flux.yaml, next to config.yaml -- yes.  Same directory, so it
        is versioned with the calibration that produced it, and config.yaml
        keeps a safe all-zero resting state.

    (A new top-level section inside config.yaml would also work -- qcal's
    Config.load() does no schema validation and save() round-trips unknown
    keys, so it would be inert.  A separate file just keeps ownership clean:
    qcal owns config.yaml, the site owns this one.)
    """
    path = os.path.join(calib_dir, "coupler_flux.yaml")
    if not os.path.exists(path):
        return {}

    with open(path) as handle:
        return yaml.safe_load(handle).get("coupler_flux", {})


def apply_coupler_flux(cfg, active_qubits, coupler_flux):
    """Bias only the couplers touching active_qubits; hold all others at 0.

    qcal's initialize() emits a DC pulse for EVERY channel in
    config['initialize'] before each sequence (backend/qubic/transpiler.py:73),
    reading amps from the config.  On IQM20Q, energising every coupler at once
    degrades the chip, so a job that uses Q20 must bias only C16_20 and C19_20
    and leave the other 28 at zero.

    The operator derives active_qubits from the job -- the user asks for a
    qubit, never for a DC amplitude.  That keeps a hardware-damaging knob off
    the public API, the same way queue permissions already work.

    Mutates cfg in memory only (never saved); qcal reads the config at
    sequence-generation time, so calling this any time before qpu.run() is
    safe.

    Returns the channels actually biased, for the log.
    """
    if not coupler_flux:
        return {}

    applied = {}
    for channel in cfg["initialize"]:
        # 'C16_20.dc' -> {16, 20};  'C20.dc' -> {20}
        endpoints = {int(n) for n in re.findall(r"\d+", channel)}
        if endpoints & set(active_qubits):
            amp = coupler_flux.get(channel, 0.0)
        else:
            amp = 0.0
        cfg[f"initialize/{channel}/amp"] = round(amp, 5)
        if amp:
            applied[channel] = amp

    return applied
