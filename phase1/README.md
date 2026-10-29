# Qiskit Fall Fest 2026 - Phase 1: PS-S3 (Trotter Error vs Realistic Device Noise)

**Team:** QFF-S3  **Track:** Quantum Simulation  **Selected problem statement:** PS-S3

## What this repo does
Simulates the real-time evolution of a 4-spin transverse-field Ising chain
(H = -J sum Z_i Z_j - g sum X_i, J = g = 1, t = 2, initial state all spins up) with first-order
Trotterisation, and measures how **Trotter error** (falls with more steps) and **hardware noise**
(rises with more gates) combine on **Processor A** (5 qubits) and **Processor B** (9 qubits).
Both an open chain and a periodic ring are studied, because they embed very differently in the two coupling graphs.

## Run it
```bash
pip install -r requirements.txt
python validate_physics.py     # Qiskit-free checks (Trotter convergence, SWAP-free embeddings)
python main.py --quick         # ~1 min smoke test
python main.py                 # full benchmark -> results/
# or open main.ipynb and run all cells
```

## Layout
`main.ipynb` (end-to-end) | `main.py` | `src/` (problem, processors, routing, metrics, visualization, experiment, config)
| `processors/` (A/B JSON) | `results/tables`, `results/figures`, `results/environment.json` | `report.md`

## Method (summary)
- Observables: mean magnetisation `mz` and mean nearest-neighbour correlator `zz`, from Z-basis counts.
- Errors separated three ways: **Trotter error** (ideal Trotter vs exact), **noise error** (noisy vs ideal Trotter),
  **total error** (noisy vs exact). Exact and ideal-Trotter references are computed with NumPy/SciPy.
- Compilation in three stages (logical -> routed with visible SWAPs -> native `rz, sx, x, cx`) so the SWAP count is measured, not estimated.
- Layout study: `naive` (logical i -> physical i) vs `optimized` (transpiler layout, best of N routing seeds).
- Noise: depolarising error on `sx/x` and `cx` via Qiskit Aer (density-matrix simulation), `rz` noise-free.
- Reproducibility: fixed seeds, 20000 shots, standard errors reported, versions saved in `results/environment.json`.
- Self-check: ideal Aer on every compiled circuit must agree with the NumPy Trotter reference or the run aborts.

## Assumptions and limitations (read before judging results)
- **Noise values and basis gates are NOT official.** Organizers said no value is official yet; 0.005 and 0.01 CX error are both swept. Conclusions that change between them are flagged in the report.
- Processor coupling maps were transcribed from the organizers' configuration document and should match the supplied images.
- Only 4 spins, one Hamiltonian, one evolution time, first-order Trotter: results from one finite model do not establish a universal architectural advantage.
- Connectivity effects are separated from gate-set/noise effects only because both processors share the same assumed gate set and noise.

## Results
The generated benchmark tables show the expected trade-off between Trotter error and noise. For the open-chain optimized layout at $cx\_error = 0.005$ and 8 Trotter steps, both Processor A and Processor B achieve the same minimum total error for $m_z$: $0.0032297$. The same is true for $zz$: $0.1621665$.

The topology difference shows up most clearly on the periodic boundary. With the same 8-step optimized layout and $cx\_error = 0.005$, Processor B outperforms Processor A on the main observables: total $m_z$ error is $0.1902695$ vs $0.2756695$, and total $zz$ error is $0.2596955$ vs $0.3680455$. This gap is consistent with the lower routing overhead on Processor B, which uses 0 SWAPs while Processor A still requires 15 SWAPs in the optimized periodic embedding.

The full CSV outputs are stored in `results/tables/`, and the exact software environment is recorded in `results/environment.json`.

## AI assistance disclosure
Initial scaffolding for the report and documentation was drafted with GitHub Copilot. The team then reviewed the saved benchmark tables and figures, checked the numerical values against the generated CSV outputs, and finalized the interpretation and conclusions in this report.
