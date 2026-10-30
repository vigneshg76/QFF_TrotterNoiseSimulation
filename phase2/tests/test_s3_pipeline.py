import unittest

import numpy as np

import qff_sim as q
import s3_pipeline as s3


class PS_S3PipelineTests(unittest.TestCase):
    def test_locked_hamiltonian_matches_organizer_builder(self):
        stored = s3.load_locked_hamiltonian()
        built = q.tfim_hamiltonian(s3.N, s3.J, s3.G, periodic=True)
        np.testing.assert_allclose(stored.to_matrix(), built.to_matrix())

    def test_exact_evolution_preserves_initial_state_at_zero_time(self):
        initial = q.Statevector(q.trotter_circuit(s3.N, s3.J, s3.G, 0.0, 0, periodic=True))
        exact = q.exact_evolution(s3.load_locked_hamiltonian(), initial, [0.0])[0]
        self.assertAlmostEqual(q.state_fidelity(initial, exact), 1.0, places=12)

    def test_noiseless_density_matrix_matches_trotter_statevector(self):
        processor = s3.load_processors()["D"]
        circuit = s3.build_circuit(2, processor)
        ideal = q.Statevector(circuit)
        density = q.noisy_density_matrix(circuit, processor, noisy=False)
        self.assertAlmostEqual(q.state_fidelity(ideal, density), 1.0, places=10)


if __name__ == "__main__":
    unittest.main()
