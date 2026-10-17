"""Processor A/B definitions (built from the JSON files) and the noise model."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_processor(name):
    path = ROOT / "processors" / f"processor_{name}.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def make_coupling_map(spec):
    from qiskit.transpiler import CouplingMap

    edges = []
    for a, b in spec["coupling_map"]:
        edges += [(a, b), (b, a)]          # undirected connections -> both directions
    cm = CouplingMap(couplinglist=edges)
    assert cm.size() == spec["num_qubits"], "coupling map size != num_qubits"
    return cm


def make_noise_model(basis_gates, cx_error, sq_error, readout_error=0.0):
    """Depolarizing noise on sx/x (1q) and cx (2q); rz is virtual (noise-free)."""
    from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

    nm = NoiseModel(basis_gates=basis_gates)
    if sq_error > 0:
        nm.add_all_qubit_quantum_error(depolarizing_error(sq_error, 1), ["sx", "x"])
    if cx_error > 0:
        nm.add_all_qubit_quantum_error(depolarizing_error(cx_error, 2), ["cx"])
    if readout_error > 0:
        r = readout_error
        nm.add_all_qubit_readout_error(ReadoutError([[1 - r, r], [r, 1 - r]]))
    return nm
