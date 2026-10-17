"""Qiskit-free sanity checks (NumPy / SciPy / NetworkX only).  Run:  python validate_physics.py

1. Does the first-order Trotter product converge to the exact evolution as steps grow?
2. Can the 4-spin open chain / ring be embedded in Processor A / B WITHOUT any SWAP?
   (a perfect embedding exists iff the logical interaction graph is a subgraph of the coupling graph)
"""
import json
from pathlib import Path

import networkx as nx
from networkx.algorithms import isomorphism as iso

from src.config import CONFIG
from src.problem import (bonds, exact_state, observables_from_state, trotter_state)

ROOT = Path(__file__).resolve().parent


def trotter_convergence():
    n, J, g, t = CONFIG["n_spins"], CONFIG["J"], CONFIG["g"], CONFIG["t_final"]
    print("=== Ideal Trotter error vs exact (no hardware, no noise) ===")
    for b in CONFIG["boundaries"]:
        ex = observables_from_state(exact_state(n, J, g, t, b), n, b)
        print(f"\n{b} chain  exact: mz={ex['mz']:+.4f}  zz={ex['zz']:+.4f}")
        errs = {}
        for s in CONFIG["trotter_steps"] + [32, 64]:
            tr = observables_from_state(trotter_state(n, J, g, t, s, b), n, b)
            errs[s] = (abs(tr["mz"] - ex["mz"]), abs(tr["zz"] - ex["zz"]))
            print(f"  steps={s:3d}  err_mz={errs[s][0]:.5f}  err_zz={errs[s][1]:.5f}")
        assert errs[64][0] < errs[8][0] and errs[64][1] < errs[8][1], "Trotter does not converge - check signs!"
    print("\nOK: Trotter product converges to the exact evolution (signs are consistent).")


def embeddings():
    print("\n=== SWAP-free embeddings of the logical interaction graph ===")
    for name in ("A", "B"):
        spec = json.load(open(ROOT / "processors" / f"processor_{name}.json"))
        G = nx.Graph([tuple(e) for e in spec["coupling_map"]])
        for b in CONFIG["boundaries"]:
            P = nx.Graph(bonds(CONFIG["n_spins"], b))
            maps = list(iso.GraphMatcher(G, P).subgraph_monomorphisms_iter())
            msg = f"{len(maps)} perfect layouts" if maps else "NONE -> SWAPs unavoidable"
            print(f"  Processor {name} | {b:8s} chain: {msg}")


if __name__ == "__main__":
    trotter_convergence()
    embeddings()
