# Report - PS-S3: Trotter Error vs Realistic Device Noise

## 1. Problem and motivation

This benchmark studies the real-time evolution of a 4-spin transverse-field Ising model (TFIM) under first-order Trotterization. The target Hamiltonian is

$$
H = -J \sum_{i=1}^{3} Z_i Z_{i+1} - g \sum_{i=1}^{4} X_i,
$$

with $J = g = 1$, final time $t = 2$, and an initial state with all spins up. The core trade-off is straightforward: increasing the number of Trotter steps reduces the discretization error, but more steps also increase the circuit size and therefore the hardware-noise contribution. The goal is to measure where these two effects balance, and to separate the impact of the processor topology from the assumed noise model.

The benchmark compares Processor A and Processor B across both open and periodic boundaries, and it reports three error terms: Trotter error (ideal Trotter vs. exact evolution), noise error (noisy vs. ideal Trotter), and total error (noisy vs. exact).

## 2. Method

The study uses the 4-spin TFIM with open and periodic boundaries. The exact reference is evaluated numerically, and the ideal Trotterized evolution is compared against it to quantify Trotter error. The measured observables are the mean magnetization, $m_z$, and the mean nearest-neighbour correlator, $zz$, both extracted from Z-basis measurement counts.

The circuit is compiled in three stages: logical circuit generation, routing with explicit SWAP insertion, and transpilation to the native basis gates $\{rz, sx, x, cx\}$. We therefore measure the final compiled cost, including depth, CX count, SWAPs, and physical qubits used, rather than relying on a purely logical estimate. The benchmark sweeps Trotter steps $\{1, 2, 4, 8, 16\}$ and CX error assumptions $\{0.005, 0.01\}$, while fixing the shots at 20000 and the random seed at 1234. The practical noise model is the same on both processors, so topology is the main architectural variable being isolated.

## 3. Processors A and B

Processor A is a 5-qubit device with coupling map

- $[0,1], [1,2], [1,3], [3,4]$

Processor B is a 9-qubit device with coupling map

- $[0,1], [1,2], [1,6], [2,3], [2,6], [2,5], [3,4], [4,5], [5,6], [6,7], [6,8], [8,0]$

Both use the same assumed gate set and noise values, which are team assumptions rather than official hardware values. The key architectural distinction is not the gate set but the available connectivity: Processor B has a much more ring-like and connected graph, while Processor A is sparse and more constrained. This matters most for the periodic boundary, where the logical ring topology is difficult to embed on the A graph without extra SWAPs.

## 4. Results

### 4.1 Trotter error alone (ideal gates)

The ideal-gate benchmark shows the expected convergence pattern: increasing the Trotter step count reduces the Trotter error substantially. For the open chain on Processor A, the ideal-gate $m_z$ error drops from $0.6726483$ at one step to $0.0056037$ at four steps and $0.0011772$ at eight steps. For the same processor and boundary, the ideal-gate $zz$ error falls from $0.1776832$ at one step to $0.0144480$ at 16 steps.

The periodic boundary is substantially harder. For Processor A, the $m_z$ Trotter error at one step is $1.3060881$, while at eight steps it is $0.0342383$; for the correlator, the circular bound is still the tougher case, with the $zz$ Trotter error decreasing from $0.4254956$ to $0.0686989$ between 1 and 8 steps. In other words, the ring embedding does not merely add noise; it increases the intrinsic Trotter discretization difficulty when the coupling graph is not well matched to the target layout.

### 4.2 Noise error and total error vs number of steps (A and B, open and ring)

Open-chain results are nearly identical between A and B once the layout is optimized. At $cx\_error = 0.005$ and eight Trotter steps, both processors have the same total $m_z$ error, $0.0032297$, and the same total $zz$ error, $0.1621665$. This is consistent with the fact that the open-chain logical path is already easy to embed on both graphs and the optimized routing removes the SWAP overhead entirely.

The periodic boundary separates the processors much more clearly. On the optimized periodic chain at $cx\_error = 0.005$, Processor B reaches a total $m_z$ error of $0.1902695$ at eight steps, while Processor A remains at $0.2756695$. For $zz$, the same comparison is $0.2596955$ for B versus $0.3680455$ for A. The same ordering remains at $cx\_error = 0.01$: Processor B has total $m_z$ error $0.3013695$ and total $zz$ error $0.3885455$ at eight steps, compared with Processor A at $0.4167445$ and $0.5448955$. These differences are not caused by different noise assumptions or gate sets; both processors use the same gate set and the same assumed noise model.

### 4.3 Circuit cost: depth, CX, SWAPs, physical qubits (A vs B; naive vs optimized layout)

The routing overhead is the dominant lever that distinguishes the two architectures. On the open chain, optimized layout removes all SWAPs on both processors. For example, at eight steps and $cx\_error = 0.005$, the optimized open circuits use CX count 48, depth 91, and zero SWAPs on both A and B. The naive open ordering still includes SWAPs: Processor A uses 8 SWAPs at 8 steps and 17 at 16 steps, while Processor B has zero SWAPs even in the naive open layout because the hardware already matches the chain embedding.

The periodic boundary reveals the topology bottleneck most strongly. At eight steps and $cx\_error = 0.005$, Processor A optimized periodic still uses 15 SWAPs, CX count 109, and depth 221; Processor B optimized periodic uses 0 SWAPs, CX count 64, and depth 136. The same pattern persists at 16 steps: A optimized periodic uses 31 SWAPs, depth 445, and CX count 221, while B optimized periodic uses 0 SWAPs, depth 272, and CX count 128. Thus the more connected cycle-like graph of Processor B substantially reduces the routing overhead that would otherwise dominate the noise budget.

### 4.4 Optimal number of Trotter steps (table `optimal_steps.csv`)

The step count that minimizes the total error depends on the observable and boundary, but the open-chain optimum is consistently around a small number of steps. For the open-chain $m_z$ observable at $cx\_error = 0.005$, the best total errors are:

- Processor A naive: $0.0056953$ at 4 steps
- Processor A optimized: $0.0032297$ at 8 steps
- Processor B naive: $0.0032297$ at 8 steps
- Processor B optimized: $0.0032297$ at 8 steps

For the periodic boundary, the best $m_z$ result is again at 8 steps, but the minimum total error is much worse on A than on B:

- Processor A optimized periodic: $0.2756695$ at 8 steps
- Processor B optimized periodic: $0.1902695$ at 8 steps

The correlator $zz$ is noisier and less stable: the minimum in the table is often at step 1 or 8 depending on the processor, boundary, and CX error assumption. This shows that the best Trotter step count is not universal; it is tied to the observable and the embedding overhead.

### 4.5 Noise sensitivity (CX error 0.005 vs 0.01)

The noise sweep confirms the expected trend: when the assumed CX error doubles from 0.005 to 0.01, total error rises across the board. On the open optimized chain at eight steps, the total $m_z$ error increases from $0.0032297$ to $0.0059047$ and the total $zz$ error increases from $0.1621665$ to $0.2352665$ on both A and B. On the periodic optimized chain, the same increase is much larger because the circuit is already more expensive and routing-limited:

- Processor A periodic optimized, 8 steps: $m_z$ total error rises from $0.2756695$ to $0.4167445$ and $zz$ total error rises from $0.3680455$ to $0.5448955$
- Processor B periodic optimized, 8 steps: $m_z$ total error rises from $0.1902695$ to $0.3013695$ and $zz$ total error rises from $0.2596955$ to $0.3885455$

Thus the periodic chain is substantially more sensitive to the assumed CX error, and Processor B remains more robust because it pays less routing cost.

## 5. Interpretation (evidence-based)

1. What changed between A and B?

The main change is the connectivity pattern, not the gate set or the assumed hardware noise model. Both processors use the same basis gates $\{rz, sx, x, cx\}$ and the same CX error assumptions, but the periodic-chain embedding is much easier on Processor B than on Processor A. In the optimized periodic case at eight steps and $cx\_error = 0.005$, Processor A still has 15 SWAPs, depth 221, and CX count 109, while Processor B has 0 SWAPs, depth 136, and CX count 64. This difference is large enough to dominate the total error comparison.

2. Which architectural property explains it?

The decisive architectural property is degree and cycle connectivity. Processor B contains a more ring-like graph, so the periodic logical interaction can be mapped without introducing routing overhead. Processor A is sparse and less compatible with the ring, so the logical periodic boundary turns into a routing burden. The effect is visible in the benchmark table: at eight steps and $cx\_error = 0.005$, Processor A has total $m_z$ error $0.2756695$ and $zz$ error $0.3680455$, while Processor B has $0.1902695$ and $0.2596955$. At 16 steps, the pattern remains: A needs 31 SWAPs and reaches $0.4128445$ $m_z$ error, whereas B needs 0 SWAPs and reaches $0.2954445$.

3. Could gate-set or noise differences also contribute?

No. The gate set and noise model are identical across the comparison. The same CX error values are used for both processors, and the difference in total error follows the difference in routing cost. In other words, the architecture is the leading cause; the noise model merely scales the already-compiled circuit cost.

4. Did the ring vs open chain behave as the embedding analysis predicts?

Yes. The open chain is easy to embed on both processors, and once optimized, both have zero SWAPs and nearly identical total errors. At eight steps and $cx\_error = 0.005$, the open optimized circuit has depth 91 and total $m_z$ error $0.0032297$ on both A and B, with $zz$ error $0.1621665$ on both. The periodic chain shows the opposite: it remains substantially harder on A than on B because A requires SWAPs to realize the ring while B can match the ring directly. The data therefore match the embedding expectation: topology matters most when the logical graph is ring-like.

5. Did the optimal step count move with processor, boundary, or noise level?

For the open chain, the best $m_z$ result settles near eight Trotter steps on the optimized layouts. On Processor A and B, the minimum optimized open-chain $m_z$ total error is $0.0032297$ at eight steps. For the periodic chain, the best known $m_z$ minimum is also around eight steps, but the achieved value differs sharply by processor: $0.2756695$ on A compared with $0.1902695$ on B at $cx\_error = 0.005$. The correlator $zz$ is less stable and can favor one step or eight steps depending on the processor and noise assumption, which is consistent with the `optimal_steps.csv` table. In short, the best step count stays roughly in the same range, but the achieved minimum error changes significantly with connectivity and noise.

## 6. Bottlenecks and what to change for a better processor (Phase 2 readiness)

The dominant bottleneck is the missing connectivity required to realize the periodic interaction without routing overhead. The clearest evidence is in the periodic optimized circuits: Processor B uses 0 SWAPs, while Processor A still needs 15 SWAPs at eight steps and 31 SWAPs at 16 steps. That overhead drives both the depth increase and the larger noise error. The most direct improvement for Phase 2 would therefore be to add degree and cycle connectivity around the logical ring: more direct couplings between next-nearest logical neighbors or a ring-like hardware layout would remove the largest source of routing-induced error. In short, improving the graph from a sparse, more tree-like form to a ring-like structure is more valuable than changing the gate set under the current assumptions.

## 7. Limitations

This study is intentionally narrow and should be read as a controlled comparison rather than a universal statement about hardware quality. The limitations are clear:

- The noise values and basis-gate assumptions are team assumptions, not official hardware values.
- The benchmark is limited to a 4-spin TFIM with a single evolution time and a single first-order Trotterization scheme.
- The analysis is based on finite-shot sampling with standard errors reported by the code, so there is statistical uncertainty in each measured observable.
- There is no real-hardware validation in this study; the conclusions test architecture-level behavior under a modeled noise channel.

## 8. Reproducibility

The full benchmark is reproducible from the repository as follows:

```bash
pip install -r requirements.txt
python validate_physics.py
python main.py --quick
python main.py
```

The full benchmark uses the following fixed settings from `results/environment.json`:

- 4 spins
- $J = 1.0$
- $g = 1.0$
- final time $t = 2.0$
- steps $[1, 2, 4, 8, 16]$
- boundaries $[open, periodic]$
- basis gates $[rz, sx, x, cx]$
- CX error sweep $[0.005, 0.01]$
- shots $= 20000$
- seed $= 1234$
- layout modes $[naive, optimized]$
- routing trials $= 10$

All outputs are written to `results/tables/` and `results/figures/`, with software versions recorded in `results/environment.json`.

## 9. AI assistance disclosure

Initial scaffolding for the report and documentation was drafted with GitHub Copilot. The team then reviewed the saved benchmark tables and figures, checked the numerical values against the generated CSV outputs, and finalized the interpretation and conclusions in this report.

