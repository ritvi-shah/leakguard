"""30-second sanity check. Run BEFORE the full simulation:
    python smoke_test.py
Verifies: mass balance, sane pressures, leak physics, diurnal pattern, imports.
"""
import numpy as np
from core.network import build_network, SENSOR_NODES
from core.hydraulics import HydraulicSolver
from core.simulate import diurnal_multiplier

net = build_network()
solver = HydraulicSolver(net)

demands = {n: d for n, d in net.base_demand_m3s.items() if d > 0}
heads, flows, _ = solver.solve(demands)
q_src = flows["P01"]
assert abs(q_src - sum(demands.values())) < 1e-6, "mass balance violated"
print(f"[ok] mass balance: source {q_src*1000:.1f} L/s == demand {sum(demands.values())*1000:.1f} L/s")

p = {s: heads[s] - net.elevation_of(s) for s in SENSOR_NODES}
assert all(5 < v < 90 for v in p.values()), p
print("[ok] pressure heads (m):", {k: round(v, 1) for k, v in p.items()})

heads2, _, leaks2 = solver.solve(demands, {"J9": 0.0018})
p2 = heads2["J9"] - net.elevation_of("J9")
assert leaks2["J9"] > 0 and p2 < p["J9"]
print(f"[ok] leak active: {leaks2['J9']*1000:.1f} L/s at J9 - pressure drop {p['J9']-p2:.2f} m")

assert diurnal_multiplier(3.0) < 0.5 < diurnal_multiplier(8.2)
print(f"[ok] diurnal: night {diurnal_multiplier(3.0):.2f} - morning peak {diurnal_multiplier(8.2):.2f}")

print("\nALL SMOKE TESTS PASSED - run `python run_simulation.py` next.")
