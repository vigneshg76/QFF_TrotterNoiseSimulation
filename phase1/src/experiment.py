"""Runs the full A/B benchmark grid and returns a tidy DataFrame."""
import json
import platform
import sys
import time

import numpy as np
import pandas as pd

from src.config import CONFIG
from src.metrics import observables_from_counts
from src.problem import (exact_state, observables_from_state, trotter_circuit,
                         trotter_state)
from src.processors import ROOT, load_processor, make_coupling_map, make_noise_model
from src.routing import compile_circuit, select_routing_seed

OBS = ("mz", "zz")


def _versions():
    import matplotlib
    import qiskit
    import qiskit_aer
    import scipy
    return {"python": sys.version.split()[0], "platform": platform.platform(),
            "qiskit": qiskit.__version__, "qiskit_aer": qiskit_aer.__version__,
            "numpy": np.__version__, "scipy": scipy.__version__,
            "pandas": pd.__version__, "matplotlib": matplotlib.__version__}


def apply_quick(cfg):
    cfg = dict(cfg)
    cfg.update(trotter_steps=[1, 2, 4], boundaries=["periodic"], routing_trials=2,
               shots=4000, cx_error_sweep=[cfg["cx_error_main"]])
    return cfg


def run_all(cfg=CONFIG, quick=False, verbose=True):
    from qiskit_aer import AerSimulator

    cfg = apply_quick(cfg) if quick else dict(cfg)
    n, J, g, t = cfg["n_spins"], cfg["J"], cfg["g"], cfg["t_final"]
    shots, seed = cfg["shots"], cfg["seed"]

    procs = {k: load_processor(k) for k in ("A", "B")}
    cmaps = {k: make_coupling_map(v) for k, v in procs.items()}
    noise = {p: make_noise_model(cfg["basis_gates"], p, cfg["sq_error"], cfg["readout_error"])
             for p in cfg["cx_error_sweep"]}
    ideal_sim = AerSimulator(method="statevector")

    rows, compiled_store = [], {}
    for pname, spec in procs.items():
        for boundary in cfg["boundaries"]:
            exact = observables_from_state(exact_state(n, J, g, t, boundary), n, boundary)
            for mode in cfg["layout_modes"]:
                step1 = trotter_circuit(n, J, g, t, 1, boundary).measure_all(inplace=False)
                rseed = select_routing_seed(step1, cmaps[pname], mode, cfg["routing_trials"])
                for steps in cfg["trotter_steps"]:
                    qc = trotter_circuit(n, J, g, t, steps, boundary).measure_all(inplace=False)
                    comp = compile_circuit(qc, cmaps[pname], cfg["basis_gates"], mode, rseed)
                    m = comp["metrics"]
                    compiled_store[(pname, boundary, mode, steps)] = comp

                    tro = observables_from_state(trotter_state(n, J, g, t, steps, boundary), n, boundary)

                    # sanity: ideal Aer on the COMPILED circuit must match the NumPy Trotter reference
                    ic = ideal_sim.run(comp["native"], shots=shots, seed_simulator=seed).result().get_counts()
                    ido = observables_from_counts(ic, n, boundary)
                    for o in OBS:
                        tol = 5 * ido[o + "_se"] + 1e-3
                        if abs(ido[o] - tro[o]) > tol:
                            raise RuntimeError(
                                f"Sanity check failed ({pname},{boundary},{mode},steps={steps},{o}): "
                                f"ideal Aer {ido[o]:.4f} vs NumPy Trotter {tro[o]:.4f}")

                    for cxe in cfg["cx_error_sweep"]:
                        sim = AerSimulator(noise_model=noise[cxe], method="density_matrix")
                        t0 = time.perf_counter()
                        counts = sim.run(comp["native"], shots=shots, seed_simulator=seed).result().get_counts()
                        runtime = time.perf_counter() - t0
                        nz = observables_from_counts(counts, n, boundary)

                        row = {"processor": pname, "boundary": boundary, "layout": mode,
                               "steps": steps, "cx_error": cxe, "shots": shots, "seed": seed,
                               "depth": m["depth"], "cx": m["two_qubit_gates"], "swaps": m["swaps"],
                               "logical_cx": m["logical_cx"],
                               "cx_overhead_routing": m["cx_overhead_from_routing"],
                               "total_gates": m["total_gates"],
                               "physical_qubits_used": m["physical_qubits_used"],
                               "initial_layout": str(m["initial_layout"]),
                               "runtime_s": runtime}
                        for o in OBS:
                            row[f"exact_{o}"] = exact[o]
                            row[f"trotter_{o}"] = tro[o]
                            row[f"noisy_{o}"] = nz[o]
                            row[f"noisy_{o}_se"] = nz[o + "_se"]
                            row[f"err_trotter_{o}"] = abs(tro[o] - exact[o])
                            row[f"err_noise_{o}"] = abs(nz[o] - tro[o])
                            row[f"err_total_{o}"] = abs(nz[o] - exact[o])
                        rows.append(row)
                    if verbose:
                        print(f"[{pname}|{boundary}|{mode}|steps={steps}] depth={m['depth']} "
                              f"cx={m['two_qubit_gates']} swaps={m['swaps']}", flush=True)

    df = pd.DataFrame(rows)
    out = ROOT / "results"
    (out / "tables").mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "tables" / "all_results.csv", index=False)
    with open(out / "environment.json", "w", encoding="utf-8") as f:
        json.dump({"versions": _versions(), "config": cfg, "quick_mode": quick}, f, indent=2)
    make_summary_tables(df, out / "tables")
    return df, compiled_store


def make_summary_tables(df, outdir):
    # A-vs-B comparison of cost and error, one row per configuration
    vals = ["depth", "cx", "swaps", "physical_qubits_used", "err_total_mz", "err_total_zz"]
    ab = df.pivot_table(index=["boundary", "layout", "steps", "cx_error"],
                        columns="processor", values=vals)
    ab.columns = [f"{v}_{p}" for v, p in ab.columns]
    ab.reset_index().to_csv(outdir / "ab_comparison.csv", index=False)

    # Trotter-step count that minimises total error (the "sweet spot")
    recs = []
    for keys, grp in df.groupby(["processor", "boundary", "layout", "cx_error"]):
        for o in OBS:
            best = grp.loc[grp[f"err_total_{o}"].idxmin()]
            recs.append(dict(zip(["processor", "boundary", "layout", "cx_error"], keys),
                              observable=o, best_steps=int(best["steps"]),
                              min_total_error=float(best[f"err_total_{o}"]),
                              cx_at_best=int(best["cx"]), swaps_at_best=int(best["swaps"])))
    pd.DataFrame(recs).to_csv(outdir / "optimal_steps.csv", index=False)
