"""Physics for PS-S3: TFIM Hamiltonian, exact reference, ideal Trotter reference,
and the Qiskit Trotter circuit.  The NumPy references do not depend on Qiskit.

H = -J * sum_<ij> Z_i Z_j  -  g * sum_i X_i      (qubit 0 = least-significant bit)
Initial state: all spins up, |0000>  (every <Z_i> = +1).
First-order Trotter step (matches the circuit built below):
    U_step = exp(+i g dt sum X) @ exp(+i J dt sum ZZ)    (ZZ layer applied first)
"""
from functools import reduce

import numpy as np
from scipy.linalg import expm

I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)


def bonds(n, boundary):
    b = [(i, i + 1) for i in range(n - 1)]
    if boundary == "periodic" and n > 2:
        b.append((n - 1, 0))
    return b


def _op(n, ops):
    """Tensor product with qubit 0 as the least-significant (rightmost) factor."""
    return reduce(np.kron, [ops.get(q, I2) for q in reversed(range(n))])


def hamiltonian(n, J, g, boundary):
    H = np.zeros((2 ** n, 2 ** n), dtype=complex)
    for i, j in bonds(n, boundary):
        H -= J * _op(n, {i: Z, j: Z})
    for i in range(n):
        H -= g * _op(n, {i: X})
    return H


def initial_state(n):
    psi = np.zeros(2 ** n, dtype=complex)
    psi[0] = 1.0
    return psi


def exact_state(n, J, g, t, boundary):
    return expm(-1j * hamiltonian(n, J, g, boundary) * t) @ initial_state(n)


def trotter_state(n, J, g, t, steps, boundary):
    """Noise-free first-order Trotter state (matrix version of the circuit)."""
    dt = t / steps
    Hzz = sum(_op(n, {i: Z, j: Z}) for i, j in bonds(n, boundary))
    Hx = sum(_op(n, {i: X}) for i in range(n))
    step = expm(1j * g * dt * Hx) @ expm(1j * J * dt * Hzz)
    psi = initial_state(n)
    for _ in range(steps):
        psi = step @ psi
    return psi


def observables_from_state(psi, n, boundary):
    """mz = mean <Z_i>;  zz = mean nearest-neighbour <Z_i Z_j> over the Hamiltonian's bonds."""
    p = np.abs(psi) ** 2
    idx = np.arange(2 ** n)
    z = np.array([1 - 2 * ((idx >> q) & 1) for q in range(n)])
    mz = float(np.sum(p * z.mean(axis=0)))
    zz = float(np.sum(p * np.mean([z[i] * z[j] for i, j in bonds(n, boundary)], axis=0)))
    return {"mz": mz, "zz": zz}


def trotter_circuit(n, J, g, t, steps, boundary):
    """First-order Trotter circuit (no measurement).  RZZ(theta)=exp(-i theta/2 ZZ),
    RX(theta)=exp(-i theta/2 X), so exp(+i J dt ZZ) -> RZZ(-2 J dt), exp(+i g dt X) -> RX(-2 g dt)."""
    from qiskit import QuantumCircuit

    dt = t / steps
    qc = QuantumCircuit(n)
    for _ in range(steps):
        for i, j in bonds(n, boundary):
            qc.rzz(-2 * J * dt, i, j)
        for q in range(n):
            qc.rx(-2 * g * dt, q)
    return qc
