"""Single source of truth for every benchmark setting.

IMPORTANT: the noise values and the basis-gate set below are TEAM ASSUMPTIONS.
The organizers stated that the official values are NOT final, and that neither
0.005 nor 0.01 should be treated as official. Change them here (one place) when
official values are published, then re-run everything.
"""

CONFIG = {
    # --- physics (PS-S3 spec: 4-spin transverse-field Ising chain) ---
    "n_spins": 4,
    "J": 1.0,
    "g": 1.0,
    "t_final": 2.0,                 # evolution time (spec: up to 2*hbar/J)
    "trotter_steps": [1, 2, 4, 8, 16],
    "boundaries": ["open", "periodic"],

    # --- hardware assumptions (NOT official) ---
    "basis_gates": ["rz", "sx", "x", "cx"],
    "cx_error_sweep": [0.005, 0.01],   # both values appear in organizer docs; neither is official
    "cx_error_main": 0.005,
    "sq_error": 0.001,
    "readout_error": 0.0,

    # --- execution / reproducibility ---
    "shots": 20000,
    "seed": 1234,

    # --- compilation study ---
    "layout_modes": ["naive", "optimized"],   # naive = logical i -> physical i
    "routing_trials": 10,                     # routing seeds tried; best (fewest SWAPs, then depth) is kept
}
