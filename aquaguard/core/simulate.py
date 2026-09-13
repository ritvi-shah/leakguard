"""
Time-series scenario generator using WNTR/EPANET.

Leaks are modeled as EPANET emitters (orifice discharge, Q = C*sqrt(pressure)) -
the standard EPANET mechanism for pressure-dependent leakage. In leak scenarios
the leak is active from the first record; the detectors' baseline comes from
the separate no-leak scenario.
"""
import wntr
import pandas as pd

from core.network import NETWORK_PATH

PRESSURE_SENSOR_NODES = ["15", "35", "101", "105", "113", "201"]
SOURCE_LINK = "60"

NODE_LABELS = {
    "15":  "Northside Residential",
    "35":  "Downtown Commercial",
    "101": "Eastside Industrial",
    "105": "Central Park District",
    "113": "Westside Suburb",
    "201": "South Harbor Zone",
}


def generate_scenario(
    n_days: int = 14,
    leak_node: str | None = None,
    leak_start_hour: float | None = None,
    leak_coeff: float = 0.003,
    seed: int = 0,
) -> pd.DataFrame:
    wn = wntr.network.WaterNetworkModel(NETWORK_PATH)

    wn.options.time.duration = n_days * 24 * 3600
    wn.options.time.hydraulic_timestep = 900
    wn.options.time.report_timestep = 900

    if leak_node is not None:
        wn.get_node(leak_node).emitter_coefficient = leak_coeff

    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    times = results.node["pressure"].index.values
    pressures = results.node["pressure"]
    flows = results.link["flowrate"]

    rows = []
    for i, t in enumerate(times):
        row = {
            "step": i,
            "hour_of_day": (t % (24 * 3600)) / 3600,
            "source_flow_Ls": flows.loc[t, SOURCE_LINK] * 1000,
            "leak_active": int(leak_node is not None),
            "leak_node": leak_node,
        }
        for node in PRESSURE_SENSOR_NODES:
            row[f"pressure_{node}"] = pressures.loc[t, node]
        rows.append(row)

    return pd.DataFrame(rows)
