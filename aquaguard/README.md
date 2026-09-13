# AquaGuard - Predictive Water Leak Detection & Localization for Urban Water Networks

*Cloudforge Hackathon - Track 3: Social Impact & Sustainability - PS 12: Smart & Sustainable Communities*

Municipal utilities lose an estimated **30-50% of treated water** to undetected pipeline leaks
("non-revenue water"). Leaks are found reactively - a resident phones in a wet patch, days or
weeks later. AquaGuard adds the missing layer: **real-time, predictive leak detection and
localization at neighborhood level**.

**Headline result:** the industry-standard method (Minimum Night Flow) takes ~14 hours to
notice a leak. AquaGuard's digital-twin detector catches it in ~30 minutes and names the
likely leak node.

## Approach

The network is modeled as a graph; hydraulic state is solved with the same class of equations
professional tools (EPANET) use: Hazen-Williams head loss + nodal mass balance, via a
linear-theory (Wood) iterative solver, with pressure-dependent orifice emitters for leaks.

Two detectors run on the virtual sensor stream (source flow meter + 5 pressure loggers):

1. **Minimum Night Flow (MNF)** - what utilities do today: compare 02:00-04:00 flow to
   baseline. Evaluated once per night -> inherently slow.
2. **Digital-twin residual detector (ours)** - an **Isolation Forest trained only on confirmed
   no-leak telemetry** (pressures + time-of-day encoding). Deviations are flagged; the sensor
   with the largest unexpected pressure drop **localizes** the leak.

## Tech Stack

| Layer | Technology |
|---|---|
| Hydraulic simulation | Python, NetworkX, NumPy, SciPy (linear-theory solver) |
| Data generation | Pandas (14-day diurnal series, injected leak) |
| Detection - rule-based | Pandas / NumPy (MNF analysis) |
| Detection - ML | scikit-learn Isolation Forest |
| Backend / API | Flask (JSON API, cloud-deployable) |
| Frontend | HTML/CSS/vanilla JS, Chart.js (live map, scrubber) |
| Hosting | Render (gunicorn), free tier |

## Run Locally

    pip install -r requirements.txt
    python smoke_test.py        # 5-second sanity check
    python run_simulation.py    # ~1-3 min, prints metrics table
    python -m dashboard.app     # open http://localhost:8000

## Measured Results (14-day scenario, leak at node J9 from day 8, 13:00)

| Detector | Precision | Recall | F1 | Detection lag |
|---|---|---|---|---|
| Minimum Night Flow (status quo) | 1.00 | 0.90 | 0.94 | ~14 hours |
| Digital-twin ML detector (ours) | ~0.92 | 1.00 | ~0.95 | ~15-45 minutes |

Localization: the ML detector maps flagged readings to the true leak node with ~99% accuracy.
**The table printed by run_simulation.py is the authoritative measured result for your
environment** (metrics are computed, not hardcoded; MNF row is deterministic, ML row varies
slightly with library versions). MNF alerts are latched on first confirmation
(crew-dispatch semantics).

## Impact & Scalability

- Earlier detection -> less treated-water loss, lower pumping energy, less road damage.
- Graph solver + ML detector are **network-size agnostic** - same code path for 15 or 15,000 nodes.
- Sensor layer mirrors hardware real District Metered Areas already deploy.

## Data Provenance (honest disclosure)

Simulation was built from first-principles hydraulics (Hazen-Williams, mass balance, orifice
leak flow) because the dev environment had no internet to install EPANET/wntr or download the
LeakDB benchmark. Detectors consume a standard telemetry table, so swapping in real data
touches **no detection or dashboard code**:

    telemetry = pd.read_csv("leakdb_or_scada_export.csv")   # time, source_flow_lps, p_sensor_*
    results   = run_all_detectors(telemetry, meta)          # detectors unchanged

## Hackathon Compliance

All core implementation was written during the hackathon for this problem statement. Only
permissively-licensed open-source libraries were used (NumPy, Pandas, SciPy, scikit-learn,
NetworkX, Flask, Chart.js). No duplication of other teams' work.

**Disclaimer:** research prototype - not a SCADA replacement or certified engineering tool.

## Team

| Member | Role |
|---|---|
| [Name] | Hydraulics solver & simulation |
| [Name] | ML detectors & evaluation |
| [Name] | Flask API & dashboard |
| [Name] | Docs, testing, pitch |

MIT License.
