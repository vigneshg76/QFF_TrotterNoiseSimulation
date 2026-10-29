"""Circuit/resource metrics and observables from measurement counts."""
import numpy as np

from src.problem import bonds

TWO_QUBIT = {"cx", "cz", "ecr", "swap", "rzz", "rxx", "ryy"}
IGNORED = ("measure", "barrier")


def circuit_metrics(circ):
    ops = dict(circ.count_ops())
    gates = {k: v for k, v in ops.items() if k not in IGNORED}
    active = {circ.find_bit(q).index for inst in circ.data for q in inst.qubits}
    depth = circ.depth(filter_function=lambda inst: inst.operation.name not in IGNORED)
    return {
        "depth": int(depth),
        "two_qubit_gates": int(sum(v for k, v in gates.items() if k in TWO_QUBIT)),
        "total_gates": int(sum(gates.values())),
        "physical_qubits_used": len(active),
        "ops": gates,
    }


def observables_from_counts(counts, n, boundary):
    """Returns mean and standard error of mz and zz from a counts dict (logical qubit q = bit q from the right)."""
    total = sum(counts.values())
    bs = bonds(n, boundary)
    w, mz_vals, zz_vals = [], [], []
    for bitstring, c in counts.items():
        s = bitstring.replace(" ", "")
        z = [1 - 2 * int(s[n - 1 - q]) for q in range(n)]
        mz_vals.append(float(np.mean(z)))
        zz_vals.append(float(np.mean([z[i] * z[j] for i, j in bs])))
        w.append(c / total)
    w = np.array(w)
    out = {}
    for name, vals in (("mz", np.array(mz_vals)), ("zz", np.array(zz_vals))):
        mean = float(np.sum(w * vals))
        var = float(np.sum(w * (vals - mean) ** 2))
        out[name] = mean
        out[name + "_se"] = (var / total) ** 0.5
    return out
