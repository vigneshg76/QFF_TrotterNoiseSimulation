"""Compilation pipeline with explicit, countable routing.

Stage 0: logical circuit -> {rz, rx, cx}           (no hardware constraints)
Stage 1: route onto the coupling map, keeping SWAP gates visible -> SWAP count
Stage 2: translate to the native basis {rz, sx, x, cx} (each SWAP becomes 3 CX)
"""
from qiskit import transpile

from src.metrics import circuit_metrics

LOGICAL_BASIS = ["rz", "rx", "cx"]
ROUTING_BASIS = ["rz", "rx", "cx", "swap"]


def _logical(circ, seed):
    return transpile(circ, basis_gates=LOGICAL_BASIS, optimization_level=0, seed_transpiler=seed)


def _route(logical, coupling_map, mode, seed):
    kw = dict(coupling_map=coupling_map, basis_gates=ROUTING_BASIS,
              optimization_level=1, seed_transpiler=seed)
    if mode == "naive":
        kw["initial_layout"] = list(range(logical.num_qubits))   # logical i -> physical i
    return transpile(logical, **kw)                              # "optimized": transpiler picks layout


def select_routing_seed(circ_step1, coupling_map, mode, trials):
    """Pick the routing seed with fewest SWAPs (then smallest depth) using the 1-step circuit."""
    logical = _logical(circ_step1, 0)
    best = None
    for s in range(trials):
        routed = _route(logical, coupling_map, mode, s)
        key = (routed.count_ops().get("swap", 0), routed.depth())
        if best is None or key < best[0]:
            best = (key, s)
    return best[1]


def compile_circuit(circ, coupling_map, basis_gates, mode, seed):
    logical = _logical(circ, seed)
    routed = _route(logical, coupling_map, mode, seed)
    native = transpile(routed, basis_gates=basis_gates, optimization_level=1, seed_transpiler=seed)

    m = circuit_metrics(native)
    m["swaps"] = int(routed.count_ops().get("swap", 0))
    m["logical_cx"] = int(logical.count_ops().get("cx", 0))
    m["cx_overhead_from_routing"] = m["two_qubit_gates"] - m["logical_cx"]
    try:
        layout = routed.layout.initial_index_layout(filter_ancillas=True)
    except Exception:
        layout = None
    m["initial_layout"] = layout
    return {"native": native, "routed": routed, "metrics": m}
