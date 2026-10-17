"""All figures. Every figure is regenerated from results/tables/all_results.csv."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

FIG = Path(__file__).resolve().parents[1] / "results" / "figures"


def _save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=200)
    plt.close(fig)


def plot_coupling_graphs(specs):
    fig, axes = plt.subplots(1, len(specs), figsize=(5 * len(specs), 4))
    axes = np.atleast_1d(axes)
    for ax, (name, spec) in zip(axes, specs.items()):
        G = nx.Graph()
        G.add_nodes_from(range(spec["num_qubits"]))
        G.add_edges_from(map(tuple, spec["coupling_map"]))
        nx.draw(G, nx.spring_layout(G, seed=3), ax=ax, with_labels=True, node_size=700,
                node_color="#cfe3ff", edge_color="#555")
        ax.set_title(f"Processor {name}: {spec['num_qubits']} qubits, {G.number_of_edges()} couplings")
    _save(fig, "coupling_graphs.png")


def plot_error_vs_steps(df, observable="zz", layout="optimized", cx_error=0.005):
    d = df[(df.layout == layout) & (np.isclose(df.cx_error, cx_error))]
    boundaries = sorted(d.boundary.unique())
    procs = sorted(d.processor.unique())
    fig, axes = plt.subplots(len(boundaries), len(procs), figsize=(5.5 * len(procs), 4 * len(boundaries)),
                             squeeze=False, sharey=True)
    for r, b in enumerate(boundaries):
        for c, p in enumerate(procs):
            ax = axes[r][c]
            s = d[(d.boundary == b) & (d.processor == p)].sort_values("steps")
            ax.plot(s.steps, s[f"err_trotter_{observable}"], "o--", label="Trotter error (ideal gates)")
            ax.errorbar(s.steps, s[f"err_noise_{observable}"], yerr=s[f"noisy_{observable}_se"],
                        fmt="s--", label="Noise-induced error")
            ax.errorbar(s.steps, s[f"err_total_{observable}"], yerr=s[f"noisy_{observable}_se"],
                        fmt="^-", lw=2, label="Total error (noisy vs exact)")
            ax.set_xscale("log", base=2)
            ax.set_xticks(s.steps)
            ax.set_xticklabels(s.steps)
            ax.set_title(f"Processor {p} | {b} chain | layout={layout}")
            ax.set_xlabel("Trotter steps")
            ax.set_ylabel(f"|error| in <{observable}>")
            ax.grid(alpha=0.3)
            if r == 0 and c == 0:
                ax.legend(fontsize=8)
    _save(fig, f"error_vs_steps_{observable}_{layout}_cx{cx_error}.png")


def plot_error_vs_cost(df, observable="zz", layout="optimized", cx_error=0.005):
    d = df[(df.layout == layout) & (np.isclose(df.cx_error, cx_error))]
    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    for (p, b), s in d.groupby(["processor", "boundary"]):
        s = s.sort_values("cx")
        ax.plot(s.cx, s[f"err_total_{observable}"], marker="o" if p == "A" else "s",
                ls="-" if b == "open" else "--", label=f"Proc {p}, {b}")
    ax.set_xlabel("two-qubit (CX) gates in compiled circuit")
    ax.set_ylabel(f"total |error| in <{observable}>")
    ax.set_title("Total error vs circuit cost")
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    _save(fig, f"error_vs_cost_{observable}_{layout}_cx{cx_error}.png")


def plot_routing_overhead(df, steps=1):
    d = df[(df.steps == steps) & (np.isclose(df.cx_error, df.cx_error.min()))]
    d = d.drop_duplicates(["processor", "boundary", "layout"])
    labels = [f"{b}\n{l}" for b in sorted(d.boundary.unique()) for l in sorted(d.layout.unique())]
    x = np.arange(len(labels))
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, col, title in zip(axes, ["swaps", "cx"], ["SWAP gates inserted", "Total CX in compiled circuit"]):
        for k, p in enumerate(sorted(d.processor.unique())):
            vals = [d[(d.processor == p) & (d.boundary == lab.split("\n")[0]) &
                      (d.layout == lab.split("\n")[1])][col].iloc[0] for lab in labels]
            ax.bar(x + (k - 0.5) * 0.38, vals, 0.38, label=f"Processor {p}")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_title(f"{title} ({steps} Trotter step)")
        ax.legend()
        ax.grid(alpha=0.3, axis="y")
    _save(fig, f"routing_overhead_steps{steps}.png")


def plot_noise_sensitivity(df, observable="zz", layout="optimized"):
    d = df[df.layout == layout]
    boundaries = sorted(d.boundary.unique())
    procs = sorted(d.processor.unique())
    fig, axes = plt.subplots(len(boundaries), len(procs), figsize=(5.5 * len(procs), 4 * len(boundaries)),
                             squeeze=False, sharey=True)
    for r, b in enumerate(boundaries):
        for c, p in enumerate(procs):
            ax = axes[r][c]
            for cxe, s in d[(d.boundary == b) & (d.processor == p)].groupby("cx_error"):
                s = s.sort_values("steps")
                ax.errorbar(s.steps, s[f"err_total_{observable}"], yerr=s[f"noisy_{observable}_se"],
                            marker="o", label=f"CX error = {cxe}")
            ax.set_xscale("log", base=2)
            ax.set_xticks(sorted(d.steps.unique()))
            ax.set_xticklabels(sorted(d.steps.unique()))
            ax.set_title(f"Processor {p} | {b} | noise sensitivity")
            ax.set_xlabel("Trotter steps")
            ax.set_ylabel(f"total |error| in <{observable}>")
            ax.grid(alpha=0.3)
            ax.legend(fontsize=8)
    _save(fig, f"noise_sensitivity_{observable}_{layout}.png")


def save_circuit_drawings(compiled_store, key):
    """Logical-vs-compiled drawings for one configuration key (processor, boundary, layout, steps)."""
    comp = compiled_store[key]
    stem = "circuit_" + "_".join(map(str, key))
    FIG.mkdir(parents=True, exist_ok=True)
    try:
        comp["native"].draw("mpl", fold=-1, idle_wires=False).savefig(FIG / f"{stem}_native.png", dpi=150)
        plt.close("all")
    except Exception:
        (FIG / f"{stem}_native.txt").write_text(str(comp["native"].draw("text", fold=200, idle_wires=False)))


def make_all_figures(df, compiled_store=None):
    from src.processors import load_processor
    plot_coupling_graphs({k: load_processor(k) for k in ("A", "B")})
    main_cx = float(df.cx_error.min())
    for layout in sorted(df.layout.unique()):
        for obs in ("zz", "mz"):
            plot_error_vs_steps(df, obs, layout, main_cx)
    plot_error_vs_cost(df, "zz", "optimized" if "optimized" in set(df.layout) else df.layout.iloc[0], main_cx)
    plot_routing_overhead(df, steps=int(df.steps.min()))
    if df.cx_error.nunique() > 1:
        plot_noise_sensitivity(df, "zz")
    if compiled_store:
        for key in list(compiled_store)[:1]:
            save_circuit_drawings(compiled_store, key)
        for pname in ("A", "B"):
            for key in compiled_store:
                if key[0] == pname and key[3] == 1 and key[2] == "optimized":
                    save_circuit_drawings(compiled_store, key)
                    break
