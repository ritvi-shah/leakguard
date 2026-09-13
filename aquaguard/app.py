"""Root launcher: python app.py -> http://localhost:9000"""
from dashboard.app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000, debug=True)
