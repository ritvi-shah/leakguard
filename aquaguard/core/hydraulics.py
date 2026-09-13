"""Hazen-Williams hydraulic solver using the linear-theory (Wood) iterative method.

Head loss per pipe: h = r * Q^1.852, r = 10.67*L / (C^1.852 * D^4.87).
Each iteration linearizes h ~ K*Q + F around the current flow estimate, solves the
nodal continuity equations as a linear system for heads (SciPy), and updates flows
until convergence. Pressure-dependent leaks (orifice emitters, Q = c*sqrt(p)) are
wrapped in a damped outer fixed-point loop.

Sign conventions: A[node, pipe] = +1 at "from", -1 at "to"; Q > 0 flows "from"->"to".
Continuity at demand nodes (consumption d): inflow - outflow = d  =>  A @ Q = -d.
"""

import numpy as np
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import spsolve

HW_EXPONENT = 1.852
Q_FLOOR = 1e-4          # m^3/s - keeps linearized resistance finite at ~zero flow
Q_CLIP = 0.3            # m^3/s - far beyond any physical flow in this network


def hw_resistance(length_m: float, diam_m: float, c_hw: float) -> float:
    """Resistance r (m head loss per m^3/s)^1.852."""
    return 10.67 * length_m / ((c_hw ** HW_EXPONENT) * (diam_m ** 4.87))


class HydraulicSolver:
    def __init__(self, net):
        self.net = net
        self.node_ids = list(net.node_ids)
        self.nidx = {n: i for i, n in enumerate(self.node_ids)}
        self.pipe_ids = [p["id"] for p in net.pipes]
        self.r = np.array([hw_resistance(p["length_m"], p["diameter_m"], p["c_hw"])
                           for p in net.pipes])
        A = np.zeros((len(self.node_ids), len(net.pipes)))
        for k, p in enumerate(net.pipes):
            A[self.nidx[p["from_node"]], k] = 1.0     # +1 at "from" node
            A[self.nidx[p["to_node"]], k] = -1.0      # -1 at "to" node
        self.A = A
        self.fixed_mask = np.array([n == net.reservoir_id for n in self.node_ids])
        self.rows_f = np.where(self.fixed_mask)[0]
        self.rows_u = np.where(~self.fixed_mask)[0]
        self.fixed_heads = np.array([net.source_head_m])
        self._Q = np.full(len(net.pipes), 1e-3)       # warm start across timesteps

    def solve(self, demands_m3s, emitters=None, tol=1e-10, max_iter=400):
        """Returns (heads dict, pipe flows dict, leak flows dict)."""
        emitters = emitters or {}
        leak_flows = {n: 0.0 for n in emitters}
        heads = flows = None
        for _ in range(60):                            # outer loop: leak <-> pressure
            eff = dict(demands_m3s)
            for n, q in leak_flows.items():
                eff[n] = eff.get(n, 0.0) + q
            heads, flows = self._linear_theory(eff, tol, max_iter)
            if not emitters:
                break
            new_leak = {}
            for n, c in emitters.items():
                press_head = heads[n] - self.net.elevation_of(n)
                new_leak[n] = c * np.sqrt(max(press_head, 0.0))
            delta = max((abs(new_leak[n] - leak_flows[n]) for n in emitters), default=0.0)
            leak_flows = {n: 0.6 * leak_flows[n] + 0.4 * new_leak[n] for n in emitters}
            if delta < 1e-9:
                break
        return heads, flows, leak_flows

    def _linear_theory(self, demands, tol, max_iter):
        A, r, n = self.A, self.r, HW_EXPONENT
        Q = self._Q.copy()
        K_floor = n * r * (Q_FLOOR ** (n - 1.0))
        # Continuity: A @ Q = -d (demand d is consumption -> net inflow).
        rhs0 = np.zeros(len(self.node_ids))
        for node, d in demands.items():
            rhs0[self.nidx[node]] -= d
        H = np.zeros(len(self.node_ids))
        H[self.rows_f] = self.fixed_heads
        for _ in range(max_iter):
            K = np.maximum(n * r * np.abs(Q) ** (n - 1.0), K_floor)
            F = (1.0 - n) * r * Q * np.abs(Q) ** (n - 1.0)
            Kinv = 1.0 / K
            M = (A * Kinv) @ A.T                       # M*H = rhs (15x15, tiny)
            rhs = rhs0 + (A * Kinv) @ F
            M_uu = csc_matrix(M[np.ix_(self.rows_u, self.rows_u)])
            rhs_u = rhs[self.rows_u] - M[np.ix_(self.rows_u, self.rows_f)] @ self.fixed_heads
            H[self.rows_u] = spsolve(M_uu, rhs_u)
            Q_new = np.clip((A.T @ H - F) / K, -Q_CLIP, Q_CLIP)
            if np.max(np.abs(Q_new - Q)) < tol:
                Q = Q_new
                break
            Q = 0.5 * Q + 0.5 * Q_new                  # damping for looped networks
        self._Q = Q.copy()                             # warm start next timestep
        heads = {node: H[i] for node, i in self.nidx.items()}
        flows = {pid: float(Q[k]) for k, pid in enumerate(self.pipe_ids)}
        return heads, flows