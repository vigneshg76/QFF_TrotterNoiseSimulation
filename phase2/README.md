# QFF 2026 Phase 2 — PS-S3: Trotter Error vs Noise

**Team:** QFF_TrotterNoiseSimulation  
**Problem Statement:** PS-S3 (Trotter error versus noise: finding the best step count $n^*$)  
**Repository:** https://github.com/vigneshg76/QFF_TrotterNoiseSimulation  
**Primary Execution Engine:** `project/main.ipynb` (Fully executed, exit code 0)  

---

## 1. Executive Summary & Key Results

In digital quantum simulation (DQS) of Hamiltonian dynamics on noisy intermediate-scale quantum (NISQ) processors, a fundamental tension governs simulation accuracy:
1. **Algorithmic Discretization Error (Trotter Error):** Increasing the number of Trotter steps $n$ reduces discrete-time operator splitting error ($\epsilon_T \propto 1/n^2$ in infidelity for first-order Suzuki-Trotter).
2. **Decoherence & Hardware Gate Noise:** Each additional Trotter step introduces a discrete layer of non-commuting two-qubit entangling gates, accumulating depolarizing error that exponentially suppresses quantum state fidelity ($F_\text{noise} \propto e^{-\lambda_\text{step} \cdot n}$).

This competition induces a universal non-monotonic crossover peaking at an optimal step count $n^*$. This project rigorously identifies, models, and explains $n^*$ across hardware topologies (Processors A, B, and custom Processor D) and noise scales ($0.5\times, 1\times, 2\times$), under official locked benchmarks.

### Headline Benchmark Summary (Official Locked Settings)

| Processor | Topology | Native Basis | Physical Qubits | Noise Scale | $n^*$ (Optimal Steps) | Peak Fidelity $F(n^*)$ | Two-Qubit Gates at $n^*$ | Two-Qubit Depth | SWAPs / Step |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Processor A** | Star-Tree | CX-native | 5 | $1.0\times$ | **6** | **0.577419** | 66 CX | 33 | 1 SWAP |
| **Processor B** | Planar Bridge | CX-native | 9 | $1.0\times$ | **7** | **0.662816** | 56 CX | 28 | 0 SWAPs |
| **Processor D** | Double 4-Ring | **RZZ-native** | 8 | $0.5\times$ | **8** | **0.841453** | 32 RZZ | 16 | 0 SWAPs |
| **Processor D** | Double 4-Ring | **RZZ-native** | 8 | $1.0\times$ | **8** | **0.752817** | 32 RZZ | 16 | 0 SWAPs |
| **Processor D** | Double 4-Ring | **RZZ-native** | 8 | $2.0\times$ | **7** | **0.620712** | 28 RZZ | 14 | 0 SWAPs |

- **Exact Reference Observable:** Staggered Magnetization $M_s(T=2.0) = \mathbf{0.652444}$ ($|\psi_\text{exact}(T)\rangle$ via dense SciPy `expm_multiply`, norm $= 1.0000000000$).
- **Algorithmic Error Scaling:** Log-log regression of noise-free Trotter infidelity $(1 - F_\text{trot})$ vs $n$ yields a slope of $\mathbf{-1.865}$, confirming first-order Trotter theory (asymptotic slope $-2.00$).
- **Hardware Bottleneck & Processor D Advantage:**
  - *Vs Processor A:* Eliminates the tree routing bottleneck (Processor A graph girth is $\infty$, requiring 1 SWAP/step, 11 CX/step), slashing two-qubit gate count and eliminating routing overhead entirely.
  - *Vs Processor B:* Processor B natively embeds the 4-cycle but incurs 8 CX gates per step. Processor D adopts an **RZZ-native basis** (`['rz', 'sx', 'x', 'rzz']`, explicitly permitted by docx Section 6 and `tools/check_processor_d.py`), realizing each $ZZ$ bond as a single physical two-qubit gate ($4$ RZZ/step vs $8$ CX/step). This cuts two-qubit gate count and two-qubit depth by **50%**, boosting peak fidelity from $0.6628$ to $\mathbf{0.7528}$ ($+13.6\%$ relative fidelity gain, $26.7\%$ reduction in infidelity).
- **Noise Dynamics of $n^*$:** As physical error rates double ($0.5\times \to 1.0\times \to 2.0\times$), the per-step loss coefficient $\lambda_\text{step}$ scales cleanly by $2\times$ per doubling ($0.01378 \to 0.02732 \to 0.05351$, clean $1.98\times$ and $1.96\times$). Continuous parabolic peak interpolation yields $n^*(\lambda)$ power-law scaling $\alpha = \mathbf{-0.2290 \pm 0.0113}$, consistent with non-asymptotic Trotter convergence approaching the asymptotic $\lambda^{-1/3}$ scaling.
- **First-Principles $\lambda_\text{step}$ Prediction:** A parameter-free quantum channel calculation summing subsystem error channels predicts $\lambda_\text{step} = 0.02600$ for Processor D (vs measured $0.02732$, a 7.1% match) and $0.04300$ for Processor B (vs measured $0.04473$, a 6.5% match).
- **Quantum Error Mitigation:**
  - Single-qubit readout-error correction rescales raw $M_s(n^*=8)$ from $0.503174$ to $0.513443$ (32,768 calibration shots).
  - Whole-circuit digital unitary gate folding ZNE across folds {1, 3, 5, 7} with pre-readout correction yields:
    - Linear ZNE: $0.549460 \pm 0.010935$
    - Richardson ZNE: $0.634135 \pm 0.035212$
    - Zero-Asymptote Exponential ZNE: $\mathbf{0.633913 \pm 0.020965}$
  - **Decomposition of Residual Gap:** The ideal first-order Trotter observable at $n^*=8$ is $M_s^	ext{trot}(8) = \mathbf{0.618206}$ ($M_s^	ext{exact} = 0.652444$). The total raw error decomposes into **$-0.034238$ pure Trotter algorithmic bias** and **$-0.115032$ hardware noise**. Zero-asymptote exponential ZNE recovers the expectation value within $0.75\sigma$ of the ideal Trotter target!
  - **Mitigation-Optimal Step Count:** Scanning across the grid demonstrates that the post-ZNE observable error is minimized at **$n = 10$** ($M_s^\text{ZNE} = 0.62949$, $|M_s - M_s^\text{exact}| = \mathbf{0.0230}$), proving that error mitigation allows exploiting deeper Trotter circuits with smaller algorithmic bias.

---

## 2. Repository Architecture

```
project/
├── README.md                          # Executive summary, benchmark table, run instructions
├── main.ipynb                         # Standalone executable notebook (N0–N14, fully executed)
├── requirements.txt                   # Official pinned dependencies
├── qff_sim.py                         # Organizer starter module (verifiably unchanged)
├── processors/
│   └── processor_D.json               # Frozen custom hardware design (passes checker)
├── data/
│   └── s3/
│       └── tfim_ring_N4_g1.00.json    # Locked TFIM ring Hamiltonian specification
├── tools/
│   └── check_processor_d.py           # Official Processor D design rule verification script
├── templates/
│   └── results_columns.md             # Required CSV column and schema specifications
├── results/
│   ├── environment.json               # Environment metadata, SHA-256 hashes, locked parameters
│   ├── report_numbers.json            # Exact measured values consumed by report.md
│   ├── figures/                       # High-resolution benchmark figures
│   │   ├── processor_D.png            # Coupling graph of custom Processor D (Double 4-Ring)
│   │   ├── s3_crossover.png           # Multi-panel F(n) crossover curves with model fits
│   │   ├── s3_noise_sweep.png         # Noise scale sweep (0.5×, 1×, 2×) on Processor D
│   │   └── s3_gate_split.png          # Stacked gate breakdown (logical vs routing)
│   ├── tables/                        # All 7 official benchmark output tables
│   │   ├── bell.csv                   # Objective 1: Bell-state verification on Processor D
│   │   ├── resources.csv              # Resource comparison at n* and n=16 across A, B, D
│   │   ├── s3_scan.csv                # Full step scan data across processors & scales
│   │   ├── s3_summary.csv             # Measured n* and peak fidelity values
│   │   ├── s3_noise_sweep.csv         # Processor D noise scale sweep data
│   │   ├── s3_gate_split.csv          # Comprehensive gate and depth metrics vs n
│   │   └── mitigation.csv             # Bonus: Error mitigation benchmark
│   ├── auxiliary/                           # Exploratory & audit studies (Tasks T1–T8)
│   │   ├── processor_D_v1.json        # Archived v1 Processor D design (CX control)
│   │   ├── d_design_search.csv        # Comprehensive candidate evaluation (C1–C6)
│   │   ├── d_ablation.csv             # 2×2 ablation: Topology (Tree/Ring) × Basis (CX/RZZ)
│   │   ├── a_routing_lower_bound.csv  # Graph theory & exhaustive search (girth infinity)
│   │   ├── a_routing_sensitivity.csv  # 50-seed sensitivity proving 0 router variance
│   │   ├── first_principles_lambda.csv# Theoretical vs empirical decoherence rates
│   │   ├── noise_scaling.csv          # 5-scale power-law regression with parabolic peak fit
│   │   ├── bottleneck.csv             # Measured noise channel breakdown (2Q, 1Q, readout)
│   │   ├── improvements.csv           # Measured 2nd-order Suzuki & native RZZ compilation
│   │   ├── mitigation_extended.csv    # Trotter bias vs hardware noise decomposition
│   │   ├── mitigation_optimal_n.csv   # Observable error vs step count post-ZNE
│   │   └── observable_optimal.csv     # State-fidelity n*(F) vs observable n*(Ms)
│   └── cache/                         # Intermediate simulation cache (RECOMPUTE flag support)
├── phase1_archive/                    # Archived Phase 1 artifacts
└── report.md                          # Comprehensive technical report (<= 8 pages)
```

---

## 3. How to Run & Reproducibility Guarantee

### Prerequisites
A Python virtual environment running Python 3.11, 3.12, or 3.13:
```bash
python -m venv sim-env
# Activate on Windows:
sim-env\Scripts\activate
# Activate on Linux/macOS:
source sim-env/bin/activate

pip install -r requirements.txt
```

### Reproducing All Results
The notebook is self-contained and reproducible. To execute top-to-bottom:
```bash
jupyter nbconvert --to notebook --execute main.ipynb --output main_executed.ipynb
# Or via python module:
python -m jupyter nbconvert --to notebook --execute main.ipynb --output main_executed.ipynb
```
- **Execution Time:** ~30–40 seconds with `RECOMPUTE = True` (fresh density-matrix calculations, candidate search, exhaustive permutation search, and 4096-shot Aer simulations from scratch).
- **Strict Verification:** Cell N14 executes assertions verifying that every output table exists, conforms strictly to `templates/results_columns.md`, and that all locked Hamiltonian parameters and seeds are preserved.

---

## 4. AI Tool Use Declaration

In accordance with competition rules, this project declares the use of the following AI tools during development:
- **Antigravity (Google DeepMind):** Primary agentic AI coding environment and pair programmer for implementing the simulation pipeline, refactoring notebook cells N0–N14, automating QA assertions, verifying CSV schema compliance, and formatting documentation.
- **Claude (Anthropic):** Architectural planning, theoretical derivation and sanity checking of the non-asymptotic Trotter crossover model, and critical review of error mitigation and hardware trade-offs.
- **GitHub Copilot (Microsoft / OpenAI):** Code scaffolding, boilerplate completion, and exploratory scripting during initial Phase 1 development.

All physical models, Hamiltonians, initial states, boundary conditions, noise scales, Trotter ordering conventions, and transpiler pass manager settings strictly adhere to the organizer's locked specification (`qff_sim.py`, `instances_index.json`, `results_columns.md`). All benchmark numbers are produced by clean local execution without fabrication.
