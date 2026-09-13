"""Net3 network file locator (EPANET .inp)."""
import glob
import os

import wntr

_PKG = os.path.dirname(wntr.__file__)

_CANDIDATES = [
    "temp.inp", "Net3.inp", "net3.inp",
    os.path.join("data", "temp.inp"),
    os.path.join("data", "Net3.inp"),
]
_CANDIDATES += sorted(glob.glob("*.inp"))
_CANDIDATES += sorted(glob.glob(os.path.join("data", "*.inp")))
_CANDIDATES += sorted(glob.glob(os.path.join(_PKG, "**", "Net3.inp"), recursive=True))

NETWORK_PATH = next((c for c in _CANDIDATES if os.path.exists(c)), None)

if NETWORK_PATH is None:
    raise FileNotFoundError(
        "Net3 .inp file not found. Place temp.inp (or Net3.inp) in the "
        "project root or the data/ folder.")
