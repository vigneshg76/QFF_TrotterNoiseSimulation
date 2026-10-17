# Report - PS-S3: Trotter Error vs Realistic Device Noise

_Fill every section from your own measured results (results/tables, results/figures). No number should appear here that is not in a table._

## 1. Problem and motivation
(4-spin TFIM, why Trotter error and noise pull in opposite directions, what you set out to measure.)

## 2. Method
Hamiltonian, initial state, first-order Trotter circuit, observables (mz, zz), error definitions (Trotter / noise / total), exact reference.

## 3. Processors A and B
Coupling graphs (figure), qubit counts, gate set, noise model and the fact that noise values are team assumptions.

## 4. Results
### 4.1 Trotter error alone (ideal gates)
### 4.2 Noise error and total error vs number of steps (A and B, open and ring)
### 4.3 Circuit cost: depth, CX, SWAPs, physical qubits (A vs B; naive vs optimized layout)
### 4.4 Optimal number of Trotter steps (table `optimal_steps.csv`)
### 4.5 Noise sensitivity (CX error 0.005 vs 0.01)

## 5. Interpretation (evidence-based)
1. What changed between A and B?
2. Which architectural property explains it? (cycle structure, degree, SWAPs inserted - cite the numbers)
3. Could gate-set or noise differences also contribute? (same gate set / noise in both here - say so)
4. Did the ring vs open chain behave as the embedding analysis predicts (A: ring needs SWAPs; B: both embed)? If not, why?
5. Did the optimal step count move with processor, boundary, or noise level?

## 6. Bottlenecks and what to change for a better processor (Phase 2 readiness)
(Concrete: which connection or property would remove the dominant overhead, supported by your measurements.)

## 7. Limitations
Assumed noise, 4 spins, single Hamiltonian/time, first-order Trotter, statistical error (standard errors from shots), no real hardware.

## 8. Reproducibility
Commands, seeds, shots, versions (results/environment.json), runtime.

## 9. AI assistance disclosure
(As in README.)
