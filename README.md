# LeakGuard

**Continuous Leak Detection & Localization for Urban Water Networks**

LeakGuard detects and localizes pipe bursts and hidden leaks in urban water supply systems in minutes instead of days. Built on the US EPA's official Net3 benchmark network and powered by the WNTR/EPANET hydraulic engine, it identifies specific district meters to deploy repair crews immediately.

---

## 📌 The Problem vs. The Solution

Municipal utilities lose **30% to 50%** of treated water through hidden infrastructure leaks (non-revenue water). Traditional detection methods relying on resident reports are reactive, while **Minimum Night Flow (MNF)** analysis only checks system status once per night between 02:00 and 04:00.

| Feature | Legacy MNF Analysis | LeakGuard Digital Twin |
| --- | --- | --- |
| **Inspection Frequency** | Once per night (02:00–04:00) | Continuous (Every 15 minutes) |
| **Average Unattended Burst** | ~14 hours | ~30 minutes (2 consecutive steps) |
| **Gradual / Slow Leaks** | Absorbed into baseline; missed | Detected via sustained envelope deviation |
| **Spatial Localization** | Aggregated flow at source (no zone info) | Pinpointed to district zone via spatial pressure drop |

---

## 🏗️ System Architecture & Data Flow

```text
  [ EPA Net3 Network (.inp) ]
               │
               ▼
   [ WNTR / EPANET Engine ]  ──────►  Simulates 14-day 15-min hydraulics (1,344 timesteps)
               │                      Auto-calibrated orifice emitter leaks
               ▼
    [ Telemetry Pipeline ]   ──────►  Source flow + 6 district pressure readings
               │
               ▼
     [ core/detectors.py ]   ──────►  Evaluates MNF Baseline vs. Residual Digital Twin
               │
               ▼
       [ make_data.py ]      ──────►  Generates ground-truth precision/recall metrics
               │
               ▼
     [ Flask Dashboard ]     ──────►  Interactive map, verdict box, charts & .docx reports

```

---

## 🔬 Detection Methodology

1. **Digital Twin Baseline:** Learns the normal hydraulic pressure signature for each district across every 15-minute slot of the day using 2 weeks of leak-free training data.
2. **Persistent Deviation Alerting:** Live pressure is evaluated against the district's expected envelope. Random noise causes isolated fluctuations; actual leaks produce sustained drops across consecutive intervals (~30 minutes), triggering an immediate alert.
3. **Spatial Localization:** Pressure attenuation is highest near the leak site. LeakGuard normalizes pressure drops across all monitored districts to identify the suspect zone and output a confidence metric.

---

## 🧪 Benchmark Scenarios

All algorithms are evaluated live in-app against ground-truth physics simulations on the EPA Net3 network:

| Scenario | Purpose | Hydraulic Behavior |
| --- | --- | --- |
| **Burst** | Speed of detection test | Large, sudden pipe rupture requiring instant response |
| **Hidden Leak** | Sensitivity & accuracy test | Small, gradual loss that bypasses nightly MNF thresholds |
| **Baseline** | False-alarm control | 14 days of uncorrupted normal operations ("cries wolf" check) |

---

## 🛠️ Deployment & City Adaptability

LeakGuard abstracts network configuration from the core detection engine, allowing quick integration with real municipal SCADA feeds:

| Customization Task | Target Location | Description |
| --- | --- | --- |
| **District Naming** | `core/simulate.py` $\rightarrow$ `NODE_LABELS` | Map node identifiers to human-readable district names |
| **Scenario Control** | `make_data.py` $\rightarrow$ `SCENARIOS` | Configure leak nodes, magnitude, and injection times |
| **Network Topology** | `core/network.py` | Load any custom EPANET `.inp` file and update sensor IDs |

---

## 🚀 Quick Start (Local Run)

### Prerequisites

* Python 3.10 or higher
* Self-contained: Runs fully offline without external API keys

### Installation & Execution

1. **Clone the repository:**
```bash
git clone https://github.com/ritvi-shah/leakguard.git
cd leakguard

```


2. **Install dependencies:**
```bash
pip install -r requirements.txt

```


3. **Generate/Cache Simulation Data:**
```bash
python make_data.py

```


4. **Launch the Dashboard:**
```bash
python -m dashboard.app

```


*Navigate to `http://localhost:9000` in your web browser.*

> **Windows Quickstart:** Double-click `run.bat` to launch automatically. Pre-computed scenario CSVs are included for instant startup.

---

## 🧰 Tech Stack & Licensing

| Layer | Technology / Library | License |
| --- | --- | --- |
| **Hydraulic Engine** | EPANET via WNTR 1.5 | US EPA Public Domain / BSD-3 |
| **Benchmark Network** | EPA Net3 (`Net3.inp`) | US EPA Public Domain |
| **Detection Core** | Residual Digital Twin Detector | Original Work |
| **Data Processing** | NumPy, Pandas | BSD-3 |
| **Backend & Reporting** | Flask, `python-docx` | BSD-3 / MIT |

---

## 📊 Provenance & Operational Impact

* **Data Provenance:** All telemetry is derived from EPANET physics calculations on the EPA Net3 benchmark network. Synthetic leak injection against deterministic physics provides honest, quantifiable metric scoring (Precision, Recall, F1, Time-to-Alert).
* **Water & Carbon Savings:** Shaving hours off detection times directly saves millions of liters of treated water and reduces pump energy emissions.
* **Operational Efficiency:** Provides repair crews with localized pipe isolation candidates rather than broad, manual field searches.

---

## ✍️ Author & Compliance

* **Author:** Ritvi (End-to-end solo build: hydraulic modeling, calibration, detection engine, evaluation suite, Flask frontend, `.docx` generator).
* **Compliance Statement:** Developed as original work during the hackathon period using open-source libraries. No external proprietary code or pre-existing projects were duplicated.
* **Disclaimer:** Research prototype and demonstration system — not a certified engineering tool or direct SCADA replacement.
