LeakGuard
Continuous leak detection & localization for urban water networks
Finds pipe leaks in minutes instead of days — and names the districtto send the repair crew to. Runs on the EPA's official Net3 benchmarknetwork with the real EPANET hydraulic engine.

The problem
Municipal utilities lose an estimated 30–50% of treated water throughhidden pipe leaks ("non-revenue water"). Detection today is mostly reactive:a resident reports a wet patch, days after the leak began.

The industry-standard tool — Minimum Night Flow (MNF) analysis —compares each night's 02:00–04:00 flows against a baseline. It is trustedand simple, but it inspects the network once per night, so a typicalburst runs unattended for ~14 hours, and a gradual leak can be absorbedinto the baseline and never flagged.

What LeakGuard does
Digital twin — learns the normal pressure of every monitoreddistrict for every time slot of the day, using leak-free data only.
Continuous detection — every 15 minutes, live pressures are comparedwith the twin's expectation. A district running significantly below itsown normal — persistently, across consecutive readings — raises an alert.
Localization — the pattern of pressure deviations across districtsnames the likely leak zone, with a confidence share.
Operator-ready output — verdict box, evidence bars, network map withsuspect highlight, and a one-click Word assessment report (verdict,ranked evidence, pipes to isolate, measured metrics).
Architecture
EPA Net3 network (Net3.inp)        |  WNTR + EPANET engine  ->  14 days @ 15-min steps (1,344 records/scenario)  leaks = pressure-dependent orifice emitters (auto-calibrated to a target  loss rate so they are hydraulically visible and realistic)        |  core/simulate.py   -> sensor time series (source flow + 6 district pressures)  core/detectors.py  -> MNF detector (status quo) + residual-twin detector (ours)  make_data.py       -> scores both vs ground truth -> dashboard/data/results.json        |  Flask dashboard    -> verdict box, Net3 map, evidence bars, charts,                        scenario switcher, .docx incident report
How the detection works (theory)
The twin is built on a simple physical idea: in a healthy network, everydistrict has a predictable pressure signature for every hour of the day —lower during morning peaks, higher at night — driven only by legitimatedemand.

Training: for each monitored district, the average pressure is learnedper 15-minute slot of the day from two weeks of leak-free operation. Thisproduces a "normal envelope" per district.
Detection: at each step, the live pressure is compared with thatdistrict's expected value. Random sensor noise produces small, isolateddeviations; a genuine leak produces a sustained, systematic drop. Thedetector therefore alerts only when a district runs significantly belowits normal envelope across consecutive readings (~30 minutes) — whichsuppresses false alarms while catching real events quickly.
Localization: a leak lowers pressure most at the points hydraulicallyclosest to it, with the effect attenuating across the network. Thedistrict with the largest normalized deviation is reported as the likelyzone, and the share of consistent alerts expresses confidence.
Why it beats nightly checks: MNF aggregates flow at the source andonly inspects once per night, so spatial information is lost and timingis coarse. The twin instead uses spatially distributed pressurescontinuously — giving both early detection and localization.
Scenarios (controlled experiments on real physics)
Scenario	Purpose
Burst	A large, sudden failure — tests speed of detection
Hidden leak	A small, gradual loss — tests sensitivity to events the nightly method structurally misses
Baseline	Two weeks of normal operation — the false-alarm control ("does it cry wolf?")
Because the leaks are injected at known nodes, detector output can bescored against known ground truth — precision, recall, F1 andtime-to-first-alert are measured, not claimed, and are displayed livein the app's Evidence tab for every run.

City-agnostic design (what changes per deployment)
Names and scenarios are presentation config, not code:

To change	Edit
District names	core/simulate.py → NODE_LABELS
Scenario labels / leak size / leak node	make_data.py → SCENARIOS
A different city's network	point core/network.py at that city's EPANET .inp + update sensor IDs — detectors, pipeline and dashboard stay untouched
The detection pipeline consumes a standard sensor table(time, source_flow, pressure_*), so a real utility SCADA/EPANET feedreplaces the simulated one without code changes.

Run locally
Requires Python 3.10+.

pip install -r requirements.txtpython make_data.py        # EPANET sims (cached in data/*.csv after first run)python -m dashboard.app    # -> http://localhost:9000
Or on Windows, double-click run.bat. Pre-computed scenario CSVs areincluded, so the dashboard starts instantly without re-simulating.The app is fully self-contained and runs offline; no API keys orinternet connection are required.

Tech stack & licenses
Layer	Technology	License
Hydraulic engine	EPANET via WNTR 1.5	EPA public domain / BSD-3 (WNTR)
Benchmark network	EPA Net3 (Net3.inp)	US EPA public domain
Detection	Residual digital twin with persistent-deviation alerting	original work
Data handling	NumPy, Pandas	BSD-3
Backend / report	Flask, python-docx	BSD-3 / MIT
Data provenance (honest disclosure)
All telemetry is simulated from real physics: the EPA Net3 benchmarknetwork, solved by the official EPANET engine. The only synthesized elementis the placement of the leaks themselves — which is precisely what enableshonest accuracy measurement against known ground truth. No real utilitydata is used or claimed. Known simplifications: no weekday/weekend demandvariation, no sensor drift or failures, single leak per scenario.

Impact
Water: every hour of earlier detection directly reduces treated-waterlosses — and the pumping and treatment energy embedded in that water.
Operations: crews get a named district and isolation-pipe candidatesinstead of a city-wide search.
Equity: non-revenue water hits poorer communities hardest throughtariffs; reducing it lowers the cost burden of every household.
Compliance
This project was designed and implemented entirely by me, Ritvi, duringthe hackathon period. All analysis code — the hydraulic pipeline, both leakdetectors, the evaluation logic, and the dashboard — was writtenspecifically for this problem statement. Only permissively-licensedopen-source libraries are used (attributed above); their use complies withthe event rules. No pre-existing project was adapted, no other team's workis duplicated, and this submission is not entered under multiple teams.

Disclaimer: research prototype / demonstration — not a certifiedengineering tool or SCADA replacement.

Author
Role	Work
Ritvi	End-to-end solo build: hydraulic pipeline (WNTR/EPANET, leak calibration), both leak detectors and evaluation, dashboard (Flask, Net3 map, evidence visuals, Word reports), documentation and demo