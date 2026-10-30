"""PS-S3 (ring TFIM, Neel start, T = 2): Trotter error vs noise on Processors A, B and D.

Built ONLY on the organizers' qff_sim.py - keep that file UNCHANGED next to this one.
Official settings (basis gates, noise rates, seeds, shots, optimization level) are not touched here;
every required run goes through the kit's own functions.
"""
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import qff_sim as q

ROOT = Path(__file__).resolve().parent
TABLES = ROOT / "results" / "tables"
FIGS = ROOT / "results" / "figures"

# ---- locked values (Phase 2 document, Section 10) ----
N, J, G, T = 4, 1.0, 1.0, 2.0
STEPS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 14, 16]
D_SCALES = [0.5, 1.0, 2.0]          # noise sweep, Processor D only

SCAN_COLS = ["processor", "noise_scale", "steps", "fidelity_noisy", "fidelity_trotter_ideal",
             "ms_noisy", "ms_noisy_se", "ms_exact", "logical_2q", "swap_2q", "two_q"]
RES_COLS = ["ps", "circuit_label", "processor", "executable", "logical_qubits", "physical_qubits",
            "logical_2q", "two_q", "depth", "two_q_depth", "swaps", "routing_overhead_2q"]
BELL_COLS = ["pair", "pair_distance", "condition", "two_qubit_gates", "XX", "XX_se", "YY", "YY_se",
             "ZZ", "ZZ_se", "fidelity", "fidelity_se"]
TIME_GRID = np.linspace(0.0, T, 9)
ERROR_COLS = ["processor", "noise_scale", "steps", "time", "system_size", "trotter_order",
              "total_time", "J", "g", "initial_state", "noise_model", "p1", "p2",
              "p_readout_setting", "readout_included", "shots", "measurement_uncertainty",
              "exact_ms", "ideal_ms",
              "noisy_ms", "trotter_ms_abs_error", "noise_ms_abs_error", "total_ms_abs_error",
              "trotter_state_error", "fidelity_trotter_ideal", "fidelity_noisy",
              "noise_trace_distance", "depth_at_T", "two_qubit_gates_at_T"]
ERROR_SUMMARY_COLS = ["processor", "noise_scale", "steps", "trotter_ms_rmse",
                      "noise_ms_rmse", "total_ms_rmse", "max_total_ms_abs_error",
                      "trotter_state_error_rmse", "mean_noise_trace_distance",
                      "mean_trotter_infidelity", "mean_total_infidelity",
                      "depth_at_T", "two_qubit_gates_at_T", "shots",
                      "noise_model", "readout_included"]


def zz_mode_for(P):
    """Use one RZZ gate per bond on an RZZ-basis processor, CX-RZ-CX otherwise (same unitary)."""
    return "rzz" if "rzz" in P.get("basis_gates", q.BASIS_GATES) else "cx"


def build_circuit(n_steps, P):
    return q.trotter_circuit(N, J, G, T, n_steps, order=1, zz_mode=zz_mode_for(P), periodic=True)


def load_processors(d_path="processors/processor_D.json"):
    D = q.load_processor(str(ROOT / d_path))
    errs = q.validate_processor_d(D, N)
    if errs:
        raise ValueError("processor_D.json violates the rules: " + "; ".join(errs))
    return {"A": q.PROCESSOR_A, "B": q.PROCESSOR_B, "D": D}


def load_locked_hamiltonian():
    """Ring Hamiltonian from the locked data file data/s3/tfim_ring_N4_g1.00.json; checked against the
    kit's own tfim_hamiltonian(periodic=True)."""
    Hb = q.tfim_hamiltonian(N, J, G, periodic=True)
    f = ROOT / "data" / "s3" / "tfim_ring_N4_g1.00.json"
    if not f.exists():
        return Hb
    d = json.loads(f.read_text())
    Hf = q.SparsePauliOp.from_list([(lbl, c) for lbl, c in d["operator"]])
    if not np.allclose(Hf.to_matrix(), Hb.to_matrix()):
        raise RuntimeError("data/s3 operator differs from qff_sim.tfim_hamiltonian(periodic=True)")
    return Hf


def exact_reference():
    """|psi_exact(T)> and M_s(T) for the ring, Neel start."""
    Hr = load_locked_hamiltonian()
    psi0 = q.Statevector(q.trotter_circuit(N, J, G, 0.0, 0, periodic=True))   # Neel '1010'
    target = q.exact_evolution(Hr, psi0, [T])[0]
    ms_exact = q.expectations(target, q.observable_ops(N))["ms"]
    return target, ms_exact


# --------------------------------------------------------------------------------------
# Step scan (headline)
# --------------------------------------------------------------------------------------
def run_scan(procs, target, ms_exact, recompute=True, verbose=True):
    f_scan, f_res = TABLES / "s3_scan.csv", TABLES / "resources.csv"
    if not recompute and f_scan.exists() and f_res.exists():
        return pd.read_csv(f_scan), pd.read_csv(f_res)
    scan_rows, res_rows = [], []
    t0 = time.time()
    for key, P in procs.items():
        scales = D_SCALES if key == "D" else [1.0]
        for n in STEPS:
            c = build_circuit(n, P)
            m = q.circuit_metrics(c, P)
            f_ideal = float(q.state_fidelity(target, q.Statevector(c)))      # noise-free Trotter fidelity
            f_1x = None
            res_rows.append(dict(ps="S3", circuit_label=f"ring_N4_T2_n{n}", processor=key,
                                 executable=m["executable"], logical_qubits=m.get("logical_qubits"),
                                 physical_qubits=m.get("physical_qubits"), logical_2q=m.get("logical_cx"),
                                 two_q=m.get("cx"), depth=m.get("depth"), two_q_depth=m.get("two_q_depth"),
                                 swaps=m.get("swaps"), routing_overhead_2q=m.get("cx_overhead")))
            for s in scales:
                F = q.noisy_state_fidelity(c, target, P, scale=s)               # REQUIRED metric
                if s == 1.0:
                    f_1x = F
                z = q.run_z_measurement(c, P, scale=s)                          # 4096 noisy shots
                scan_rows.append(dict(processor=key, noise_scale=s, steps=n, fidelity_noisy=F,
                                      fidelity_trotter_ideal=f_ideal, ms_noisy=z["ms"],
                                      ms_noisy_se=z["ms_se"], ms_exact=ms_exact,
                                      logical_2q=m["logical_cx"], swap_2q=m["cx_overhead"], two_q=m["cx"]))
            if verbose:
                print(f"[{key}] n={n:2d}  2q={m['cx']:3d} (logical {m['logical_cx']}, routing {m['cx_overhead']}) "
                      f"swaps={m['swaps']}  F(1x)={f_1x:.4f}   [{time.time() - t0:.0f}s]", flush=True)
    scan, res = pd.DataFrame(scan_rows)[SCAN_COLS], pd.DataFrame(res_rows)[RES_COLS]
    TABLES.mkdir(parents=True, exist_ok=True)
    scan.to_csv(f_scan, index=False)
    res.to_csv(f_res, index=False)
    return scan, res


def run_error_analysis(procs, resources):
    """Supplementary time-resolved error decomposition; does not alter locked T=2 runs."""
    H = load_locked_hamiltonian()
    psi0 = q.Statevector(q.trotter_circuit(N, J, G, 0.0, 0, periodic=True))
    exact_states = q.exact_evolution(H, psi0, TIME_GRID)
    ms_op = q.observable_ops(N)["ms"]
    cases = [("A", 1.0), ("B", 1.0), ("D", 0.0)]
    cases.extend(("D", scale) for scale in D_SCALES)
    raw_rows = []
    summary_rows = []

    for processor, scale in cases:
        P = procs[processor]
        for steps in STEPS:
            metrics = resources[
                (resources.processor == processor)
                & resources.circuit_label.eq(f"ring_N4_T2_n{steps}")
            ].iloc[0]
            measurements = []
            for t, exact in zip(TIME_GRID, exact_states):
                circuit = q.trotter_circuit(
                    N, J, G, float(t), steps, order=1, zz_mode=zz_mode_for(P), periodic=True
                )
                ideal = q.Statevector(circuit)
                rho = q.noisy_density_matrix(circuit, P, scale=scale, noisy=(scale != 0.0))
                exact_ms = q.expectations(exact, {"ms": ms_op})["ms"]
                ideal_ms = q.expectations(ideal, {"ms": ms_op})["ms"]
                noisy_ms = q.expectations(rho, {"ms": ms_op})["ms"]
                ideal_fidelity = float(q.state_fidelity(exact, ideal))
                noisy_fidelity = float(q.state_fidelity(exact, rho))
                ideal_rho = np.outer(ideal.data, ideal.data.conj())
                delta = rho.data - ideal_rho
                trace_distance = float(
                    0.5 * np.sum(np.abs(np.linalg.eigvalsh((delta + delta.conj().T) / 2)))
                )
                row = dict(
                    processor=processor, noise_scale=scale, steps=steps, time=float(t),
                    system_size=N, trotter_order=1, total_time=T, J=J, g=G,
                    initial_state="Neel 1010",
                    noise_model="official depolarizing gate noise",
                    p1=q.P1_DEPOL * scale, p2=q.P2_DEPOL * scale,
                    p_readout_setting=q.P_READOUT * scale, readout_included=False, shots=0,
                    measurement_uncertainty="not applicable: deterministic density-matrix simulation",
                    exact_ms=exact_ms, ideal_ms=ideal_ms,
                    noisy_ms=noisy_ms, trotter_ms_abs_error=abs(ideal_ms - exact_ms),
                    noise_ms_abs_error=abs(noisy_ms - ideal_ms),
                    total_ms_abs_error=abs(noisy_ms - exact_ms),
                    trotter_state_error=float(q.state_error(ideal, exact)),
                    fidelity_trotter_ideal=ideal_fidelity, fidelity_noisy=noisy_fidelity,
                    noise_trace_distance=trace_distance, depth_at_T=int(metrics["depth"]),
                    two_qubit_gates_at_T=int(metrics["two_q"]),
                )
                raw_rows.append(row)
                measurements.append(row)

            def rmse(values):
                return float(np.sqrt(np.mean(np.square(values))))

            summary_rows.append(dict(
                processor=processor, noise_scale=scale, steps=steps,
                trotter_ms_rmse=rmse([r["ideal_ms"] - r["exact_ms"] for r in measurements]),
                noise_ms_rmse=rmse([r["noisy_ms"] - r["ideal_ms"] for r in measurements]),
                total_ms_rmse=rmse([r["noisy_ms"] - r["exact_ms"] for r in measurements]),
                max_total_ms_abs_error=max(r["total_ms_abs_error"] for r in measurements),
                trotter_state_error_rmse=rmse([r["trotter_state_error"] for r in measurements]),
                mean_noise_trace_distance=float(np.mean([r["noise_trace_distance"] for r in measurements])),
                mean_trotter_infidelity=float(np.mean([1 - r["fidelity_trotter_ideal"] for r in measurements])),
                mean_total_infidelity=float(np.mean([1 - r["fidelity_noisy"] for r in measurements])),
                depth_at_T=int(metrics["depth"]), two_qubit_gates_at_T=int(metrics["two_q"]),
                shots=0, noise_model="official gate-noise model",
                readout_included=False,
            ))

    raw = pd.DataFrame(raw_rows)[ERROR_COLS]
    summary = pd.DataFrame(summary_rows)[ERROR_SUMMARY_COLS]
    raw.to_csv(TABLES / "s3_error_analysis.csv", index=False)
    summary.to_csv(TABLES / "s3_error_summary.csv", index=False)
    return raw, summary


def plot_error_analysis(raw, summary):
    ideal = summary[summary.noise_scale == 0.0]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    available_steps = sorted(raw.steps.unique())
    selected_steps = sorted({available_steps[0], available_steps[len(available_steps) // 2],
                             available_steps[-1]})
    for steps in selected_steps:
        g = raw[(raw.processor == "D") & (raw.noise_scale == 1.0) & (raw.steps == steps)]
        ax.plot(g.time, g.ideal_ms, marker="o", label=f"ideal, n={steps}")
    noisy_steps = selected_steps[len(selected_steps) // 2]
    g = raw[(raw.processor == "D") & (raw.noise_scale == 1.0) & (raw.steps == noisy_steps)]
    ax.plot(g.time, g.exact_ms, "k--", lw=2, label="exact")
    ax.plot(g.time, g.noisy_ms, "s-", label=f"D noisy, n={noisy_steps}, 1×")
    ax.set(title="Staggered magnetization across time", xlabel="Evolution time t",
           ylabel="Staggered magnetization Mₛ")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, ncol=2)
    _save(fig, "s3_observable_dynamics.png")

    fig, ax = plt.subplots(figsize=(7, 4.5))
    g = ideal[ideal.processor == "D"].sort_values("steps")
    ax.plot(g.steps, g.trotter_ms_rmse, "o-", label="Mₛ RMSE (ideal vs exact)")
    ax.set(title="Noise-free Trotter error over sampled times", xlabel="Trotter steps n",
           ylabel="Mₛ RMSE over t ∈ [0, 2]")
    ax.grid(alpha=0.3)
    ax.legend()
    _save(fig, "s3_trotter_error_vs_steps.png")

    fig, ax = plt.subplots(figsize=(8, 5))
    ideal_d = ideal[ideal.processor == "D"].sort_values("steps")
    ax.plot(ideal_d.steps, ideal_d.trotter_ms_rmse, "k--", marker="o", label="D, no noise")
    for scale in D_SCALES:
        g = summary[(summary.processor == "D") & (summary.noise_scale == scale)].sort_values("steps")
        ax.plot(g.steps, g.total_ms_rmse, marker="o", label=f"D, {scale:g}×")
    ax.set(title="Total staggered-magnetization error versus Trotter steps",
           xlabel="Trotter steps n", ylabel="Mₛ RMSE over t ∈ [0, 2]")
    ax.grid(alpha=0.3)
    ax.legend()
    _save(fig, "s3_total_error_vs_steps_noise.png")

    heat = summary[summary.processor == "D"].pivot(
        index="noise_scale", columns="steps", values="total_ms_rmse"
    ).sort_index()
    fig, ax = plt.subplots(figsize=(9, 3.8))
    image = ax.imshow(heat.to_numpy(), aspect="auto", interpolation="nearest", cmap="viridis")
    ax.set_xticks(np.arange(len(heat.columns)), labels=heat.columns)
    ax.set_yticks(np.arange(len(heat.index)), labels=[f"{v:g}×" for v in heat.index])
    ax.set(title="D: total Mₛ RMSE across noise and step count",
           xlabel="Trotter steps n", ylabel="Noise scale")
    fig.colorbar(image, ax=ax, label="Mₛ RMSE over t ∈ [0, 2]")
    _save(fig, "s3_error_heatmap.png")

    res = summary[summary.noise_scale == 1.0]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3))
    for processor in ("A", "B", "D"):
        g = res[res.processor == processor].sort_values("steps")
        axes[0].plot(g.steps, g.two_qubit_gates_at_T, marker="o", label=processor)
        axes[1].plot(g.steps, g.depth_at_T, marker="o", label=processor)
    axes[0].set(title="Two-qubit gate count", xlabel="Trotter steps n", ylabel="Gates")
    axes[1].set(title="Transpiled circuit depth", xlabel="Trotter steps n", ylabel="Depth")
    for ax in axes:
        ax.grid(alpha=0.3)
        ax.legend(title="Processor")
    _save(fig, "s3_circuit_cost_vs_steps.png")


def summarize(scan):
    """n* = n with the highest noisy fidelity (smallest n on ties; argmax returns the first maximum)."""
    rows = []
    for (p, s), g in scan.groupby(["processor", "noise_scale"]):
        g = g.sort_values("steps")
        i = int(np.argmax(g["fidelity_noisy"].to_numpy()))
        rows.append(dict(processor=p, noise_scale=s, n_star=int(g.iloc[i]["steps"]),
                         fidelity_at_n_star=float(g.iloc[i]["fidelity_noisy"])))
    out = pd.DataFrame(rows)
    out.to_csv(TABLES / "s3_summary.csv", index=False)
    return out


# --------------------------------------------------------------------------------------
# Objective 1: Bell state on Processor D
# --------------------------------------------------------------------------------------
def bell_pairs(D):
    """(directly connected pair, farthest-apart pair) of PHYSICAL qubits in D."""
    cm = q.coupling_map_from_edges(D["edges"], D["num_qubits"])
    near = tuple(D["edges"][0])
    far = max(((a, b) for a in range(D["num_qubits"]) for b in range(a + 1, D["num_qubits"])),
              key=lambda ab: cm.distance(*ab))
    return near, far


def run_bell(D):
    rows = []
    for pair in bell_pairs(D):
        for noisy in (False, True):
            r = q.bell_experiment(D, pair, noisy)
            rows.append(dict(pair=str(pair), pair_distance=r["pair_distance"],
                             condition="noisy" if noisy else "ideal", two_qubit_gates=r["cx"],
                             XX=r["XX"], XX_se=r["XX_se"], YY=r["YY"], YY_se=r["YY_se"],
                             ZZ=r["ZZ"], ZZ_se=r["ZZ_se"], fidelity=r["fidelity"],
                             fidelity_se=r["fidelity_se"]))
    df = pd.DataFrame(rows)[BELL_COLS]
    df.to_csv(TABLES / "bell.csv", index=False)
    return df


# --------------------------------------------------------------------------------------
# Bonus: readout-error mitigation of M_s at n* on D
# --------------------------------------------------------------------------------------
def readout_mitigation(D, n_star):
    """Official readout error = symmetric bit flip p per qubit, so a measured <Z_i> is shrunk by
    (1 - 2p). Calibration: measure the all-zeros state (empty circuit) -> <Z_0> = 1 - 2p. Then
    M_s(mitigated) = M_s(raw) / (1 - 2p). Corrects READOUT error only (gate noise remains).
    The model assumption (symmetric, independent flips) holds for the official noise model; a real
    device would need a full calibration matrix."""
    c = build_circuit(n_star, D)
    raw = q.run_z_measurement(c, D)
    cal = q.run_z_measurement(q.QuantumCircuit(N), D)        # calibration: 4096 extra shots
    factor = cal["z0"]
    row = dict(method="readout correction (symmetric-flip calibration)", ms_raw=raw["ms"],
               ms_mitigated=raw["ms"] / factor, extra_shots=q.SHOTS)
    df = pd.DataFrame([row])
    df.to_csv(TABLES / "mitigation.csv", index=False)
    return df, factor


# --------------------------------------------------------------------------------------
# Figures
# --------------------------------------------------------------------------------------
def _save(fig, name):
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIGS / name, dpi=200)
    plt.close(fig)


def plot_fidelity_scan(scan, summary):
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.3), sharey=True)
    for ax, p in zip(axes, ["A", "B", "D"]):
        g = scan[(scan.processor == p) & np.isclose(scan.noise_scale, 1.0)].sort_values("steps")
        ns = summary[(summary.processor == p) & np.isclose(summary.noise_scale, 1.0)].iloc[0]
        ax.plot(g.steps, g.fidelity_trotter_ideal, "o--", label="noise-free Trotter")
        ax.plot(g.steps, g.fidelity_noisy, "s-", lw=2, label="noisy (official model, 1x)")
        ax.axvline(ns.n_star, color="gray", ls=":", label=f"n* = {int(ns.n_star)}")
        ax.set(title=f"Processor {p}", xlabel="Trotter steps n", ylabel="state fidelity F")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    _save(fig, "s3_fidelity_vs_steps.png")


def plot_noise_sweep(scan, summary):
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for s in D_SCALES:
        g = scan[(scan.processor == "D") & np.isclose(scan.noise_scale, s)].sort_values("steps")
        ns = summary[(summary.processor == "D") & np.isclose(summary.noise_scale, s)].iloc[0]
        ax.plot(g.steps, g.fidelity_noisy, "o-", label=f"{s}x noise (n* = {int(ns.n_star)})")
    ax.set(title="Processor D: noise sweep", xlabel="Trotter steps n", ylabel="noisy state fidelity F")
    ax.grid(alpha=0.3)
    ax.legend()
    _save(fig, "s3_noise_sweep_D.png")


def plot_gate_split(scan):
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.3), sharey=True)
    for ax, p in zip(axes, ["A", "B", "D"]):
        g = scan[(scan.processor == p) & np.isclose(scan.noise_scale, 1.0)].sort_values("steps")
        x = np.arange(len(g))
        ax.bar(x, g.logical_2q, label="logical Trotter gates")
        ax.bar(x, g.swap_2q, bottom=g.logical_2q, label="routing gates (from SWAPs)")
        ax.set_xticks(x)
        ax.set_xticklabels(g.steps)
        ax.set(title=f"Processor {p}", xlabel="Trotter steps n", ylabel="two-qubit gates")
        ax.legend(fontsize=8)
    _save(fig, "s3_gate_split.png")


def plot_ms(scan):
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.3), sharey=True)
    for ax, p in zip(axes, ["A", "B", "D"]):
        g = scan[(scan.processor == p) & np.isclose(scan.noise_scale, 1.0)].sort_values("steps")
        ax.errorbar(g.steps, g.ms_noisy, yerr=g.ms_noisy_se, fmt="s-", label="noisy shots (4096)")
        ax.axhline(g.ms_exact.iloc[0], color="k", ls="--", label="exact M_s(T)")
        ax.set(title=f"Processor {p}", xlabel="Trotter steps n", ylabel="staggered magnetization M_s")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    _save(fig, "s3_ms_vs_steps.png")


def make_figures(scan, summary):
    plot_fidelity_scan(scan, summary)
    plot_noise_sweep(scan, summary)
    plot_gate_split(scan)
    plot_ms(scan)


def plot_processor_graphs(procs):
    """Coupling graphs of A, B and D (the D drawing is required in the report)."""
    import networkx as nx
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.3))
    for ax, (k, P) in zip(axes, procs.items()):
        G = nx.Graph()
        G.add_nodes_from(range(P["num_qubits"]))
        G.add_edges_from(map(tuple, P["edges"]))
        nx.draw(G, nx.spring_layout(G, seed=3), ax=ax, with_labels=True, node_size=650, node_color="#cfe3ff")
        ax.set_title(f"Processor {k}: {P['num_qubits']} qubits, {G.number_of_edges()} couplings, "
                     f"basis {P.get('basis_gates', q.BASIS_GATES)[-1]}", fontsize=9)
    _save(fig, "processor_graphs.png")


def save_environment():
    import matplotlib as mpl
    import qiskit
    import qiskit_aer
    import scipy
    info = {"python": sys.version.split()[0], "platform": platform.platform(), "qiskit": qiskit.__version__,
            "qiskit_aer": qiskit_aer.__version__, "numpy": np.__version__, "scipy": scipy.__version__,
            "pandas": pd.__version__, "matplotlib": mpl.__version__,
            "official": {"opt_level": q.OPT_LEVEL, "seed": q.SEED, "shots": q.SHOTS}}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "environment.json").write_text(json.dumps(info, indent=2))


def run_everything(recompute=True, bonus=True, save_env=True):
    TABLES.mkdir(parents=True, exist_ok=True)
    procs = load_processors()
    target, ms_exact = exact_reference()
    print(f"exact M_s(T={T}) = {ms_exact:.5f}")
    scan, res = run_scan(procs, target, ms_exact, recompute)
    summary = summarize(scan)
    print(summary.to_string(index=False))
    error_data, error_summary = run_error_analysis(procs, res)
    plot_error_analysis(error_data, error_summary)
    bell = run_bell(procs["D"])
    print(bell.to_string(index=False))
    mit = None
    if bonus:
        n_star = int(summary[(summary.processor == "D") & np.isclose(summary.noise_scale, 1.0)].n_star.iloc[0])
        mit, factor = readout_mitigation(procs["D"], n_star)
        print(mit.to_string(index=False), f"| calibration factor (1-2p) = {factor:.4f}")
    make_figures(scan, summary)
    plot_processor_graphs(procs)
    try:
        if save_env:
            save_environment()
    except Exception as e:                      # environment info is nice-to-have
        print("could not save environment.json:", e)
    return scan, summary, res, bell, mit


if __name__ == "__main__":
    if "--quick" in sys.argv:
        # smoke test only: 2 step counts, 1x noise, written to results_quick/ (never mix with the real results)
        STEPS[:] = [1, 4]
        D_SCALES[:] = [1.0]
        TABLES = ROOT / "results_quick" / "tables"
        FIGS = ROOT / "results_quick" / "figures"
        run_everything(bonus=False, save_env=False)
    else:
        run_everything()
