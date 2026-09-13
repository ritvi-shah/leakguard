#!/usr/bin/env python3
# fix_server.py - installs the matching backend (port 8080) plus a root-level
# launcher, then verifies it imports cleanly.
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

APP_PY = r'''"""FlowSentry backend. Run: python -m dashboard.app -> http://localhost:8080"""
import json
import os

from flask import Flask, jsonify, render_template

APP_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(APP_DIR, "data", "results.json")
app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/data")
def api_data():
    if not os.path.exists(RESULTS):
        return jsonify(error="results.json missing - run: python run_pipeline.py"), 500
    with open(RESULTS) as f:
        return jsonify(json.load(f))


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
'''

ROOT_APP = r'''"""Root launcher so both `python app.py` and `python -m dashboard.app` work."""
from dashboard.app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
'''


def main():
    os.makedirs(os.path.join(ROOT, "dashboard"), exist_ok=True)
    with open(os.path.join(ROOT, "dashboard", "app.py"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(APP_PY)
    print("wrote dashboard/app.py  (port 8080, /api/data route)")
    with open(os.path.join(ROOT, "app.py"), "w",
              encoding="utf-8", newline="\n") as f:
        f.write(ROOT_APP)
    print("wrote app.py (root launcher, same app)")

    sys.path.insert(0, ROOT)
    os.chdir(ROOT)
    try:
        from dashboard.app import app  # noqa
        print("\nVERIFY OK: backend imports, routes /  /api/data  /healthz")
        print("START IT WITH:  python -m dashboard.app   ->   http://localhost:8080")
    except Exception as e:
        import traceback
        print("\nVERIFY FAILED - paste this traceback in the chat:")
        traceback.print_exc()


if __name__ == "__main__":
    main()