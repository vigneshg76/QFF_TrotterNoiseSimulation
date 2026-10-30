"""Processor D design helper (needs only networkx; Qiskit NOT required for the analysis).

    python design_d.py                      # compare candidate graphs (and A, B) on the numbers that matter
    python design_d.py --write ring4_tail2 --basis rzz --team "YOUR TEAM"   # write processors/processor_D.json

The written file contains a deliberately SHORT placeholder justification, so the official checker
(tools/check_processor_d.py) fails until you replace it with your own paragraph (>= 40 words)
based on what YOU measured on Processors A and B.
"""
import argparse
import json
from pathlib import Path

import networkx as nx
from networkx.algorithms import isomorphism as iso

A_EDGES = [(0, 1), (1, 2), (1, 3), (3, 4)]
B_EDGES = [(0, 1), (1, 2), (1, 6), (2, 3), (2, 6), (2, 5), (3, 4), (4, 5), (5, 6), (6, 7), (6, 8), (8, 0)]

CANDIDATES = {                                   # EXAMPLES - you are expected to design/justify your own
    "A (reference)": (5, A_EDGES),
    "B (reference)": (9, B_EDGES),
    "ring4": (4, [(0, 1), (1, 2), (2, 3), (3, 0)]),
    "ring4_tail2": (6, [(0, 1), (1, 2), (2, 3), (3, 0), (3, 4), (4, 5)]),
    "ladder2x3": (6, [(0, 1), (1, 2), (3, 4), (4, 5), (0, 3), (1, 4), (2, 5)]),
    "ring4_chord": (4, [(0, 1), (1, 2), (2, 3), (3, 0), (0, 2)]),
}
KEYS = {k.split()[0]: k for k in CANDIDATES}     # short names for --write


def describe(n, edges):
    G = nx.Graph()
    G.add_nodes_from(range(n))
    G.add_edges_from(edges)
    ring = nx.cycle_graph(4)                                           # the PS-S3 interaction graph
    n_ring = sum(1 for _ in iso.GraphMatcher(G, ring).subgraph_monomorphisms_iter())
    dist = dict(nx.all_pairs_shortest_path_length(G))
    far = max(((a, b) for a in range(n) for b in range(a + 1, n)), key=lambda ab: dist[ab[0]][ab[1]])
    return {"qubits": n, "couplings": len(edges), "max_degree": max(d for _, d in G.degree()),
            "connected": nx.is_connected(G), "ring_swap_free_layouts": n_ring,
            "diameter": dist[far[0]][far[1]], "farthest_pair": far}


def compare():
    print(f"{'design':16s} {'qubits':>6s} {'links':>5s} {'maxdeg':>6s} {'conn':>5s} "
          f"{'ring SWAP-free layouts':>22s} {'diameter':>8s} {'far pair':>9s}")
    for name, (n, e) in CANDIDATES.items():
        d = describe(n, e)
        print(f"{name:16s} {d['qubits']:6d} {d['couplings']:5d} {d['max_degree']:6d} {str(d['connected']):>5s} "
              f"{d['ring_swap_free_layouts']:22d} {d['diameter']:8d} {str(d['farthest_pair']):>9s}")
    print("\nring SWAP-free layouts = 0  ->  the PS-S3 ring cannot be placed without routing gates.")
    print("Two-qubit gates per Trotter step before routing: 8 on a CX basis (4 bonds x CX-RZ-CX), "
          "4 on an RZZ basis (4 bonds x 1 RZZ).")


def write(key, basis, team, out="processors/processor_D.json"):
    n, edges = CANDIDATES[KEYS[key]]
    gates = {"cx": ["rz", "sx", "x", "cx"], "cz": ["rz", "sx", "x", "cz"], "rzz": ["rz", "sx", "x", "rzz"]}[basis]
    d = {"name": "Processor D", "team": team, "problem_statement": "PS-S3", "num_qubits": n,
         "edges": [list(e) for e in edges], "basis_gates": gates,
         "error_rates": {"p1": 0.001, "p2": 0.005, "p_readout": 0.01},      # official values (may not be better)
         "justification": "TODO: write your own justification here from your measured results."}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(d, indent=2))
    print("wrote", out, "- now replace the justification (>= 40 words) and run tools/check_processor_d.py")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", help="candidate key: ring4, ring4_tail2, ladder2x3, ring4_chord")
    ap.add_argument("--basis", default="cx", choices=["cx", "cz", "rzz"])
    ap.add_argument("--team", default="YOUR_TEAM_NAME")
    a = ap.parse_args()
    write(a.write, a.basis, a.team) if a.write else compare()
