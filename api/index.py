"""
Flask API wrapper around the HackIllinois 2026 trading pipeline.
Endpoints:
  GET  /api/trades      - returns recent trades from sentiment_output.csv
  GET  /api/news/stream - SSE stream of new rows from sentiment_output.csv
  POST /api/config      - sets API keys for Groq and Kalshi
  POST /api/start       - launches python main.py as a subprocess
  POST /api/pause       - terminates the main.py subprocess
  GET  /api/status      - returns {running, configured}
  GET  /api/logs        - SSE stream of main.py stdout/stderr
"""

import os
import sys
import csv
import json
import threading
import subprocess
from collections import deque
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

app = Flask(__name__)
CORS(app)

CSV_PATH = os.path.join(ROOT, "sentiment_output.csv")
MAIN_PY  = os.path.join(ROOT, "main.py")

# --- Subprocess + log state ---
_proc = None
_log_lines = deque(maxlen=200)   # circular buffer of recent log lines
_log_lock = threading.Lock()
_configured = False


def _reader_thread(proc):
    """Background thread: reads proc stdout and appends to _log_lines."""
    for raw in proc.stdout:
        line = raw.rstrip()
        with _log_lock:
            _log_lines.append(line)
    proc.stdout.close()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/trades", methods=["GET"])
def get_trades():
    """Return the last 20 rows from sentiment_output.csv as JSON."""
    if not os.path.exists(CSV_PATH):
        return jsonify([])
    rows = []
    try:
        with open(CSV_PATH, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(rows[-20:][::-1])


@app.route("/api/news/stream", methods=["GET"])
def stream_news():
    """SSE stream of new rows from sentiment_output.csv."""
    def generate():
        import time
        last_count = 0
        # Send initial snapshot (last 10 rows)
        if os.path.exists(CSV_PATH):
            try:
                with open(CSV_PATH, newline="") as f:
                    rows = list(csv.DictReader(f))
                for row in rows[-10:]:
                    yield f"data: {json.dumps(row)}\n\n"
                last_count = len(rows)
            except Exception:
                pass
        # Then stream new rows as they arrive
        while True:
            time.sleep(2)
            if not os.path.exists(CSV_PATH):
                continue
            try:
                with open(CSV_PATH, newline="") as f:
                    rows = list(csv.DictReader(f))
            except Exception:
                continue
            if len(rows) > last_count:
                for row in rows[last_count:]:
                    yield f"data: {json.dumps(row)}\n\n"
                last_count = len(rows)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/config", methods=["POST"])
def configure():
    """Set API keys in os.environ so the subprocess inherits them."""
    global _configured
    data = request.get_json() or {}

    groq_key           = data.get("groq_key", "").strip()
    kalshi_api_key     = data.get("kalshi_api_key", "").strip()
    kalshi_private_key = data.get("kalshi_private_key", "").strip()

    if groq_key:
        os.environ["GROQ_API_KEY"] = groq_key
    if kalshi_api_key:
        os.environ["KALSHI_API_KEY"] = kalshi_api_key
    if kalshi_private_key:
        os.environ["KALSHI_PRIVATE_KEY"] = kalshi_private_key

    _configured = bool(groq_key and kalshi_api_key and kalshi_private_key)
    return jsonify({"status": "configured", "configured": _configured})


@app.route("/api/start", methods=["POST"])
def start_pipeline():
    """Spawn python main.py as a subprocess. Inherits env vars set by /api/config."""
    global _proc
    if _proc and _proc.poll() is None:
        return jsonify({"status": "already_running"})

    with _log_lock:
        _log_lines.clear()

    # -u = unbuffered so we get output line-by-line in real time
    _proc = subprocess.Popen(
        [sys.executable, "-u", MAIN_PY],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=os.environ.copy(),
    )
    threading.Thread(target=_reader_thread, args=(_proc,), daemon=True).start()
    return jsonify({"status": "started"})


@app.route("/api/pause", methods=["POST"])
def pause_pipeline():
    """Terminate the main.py subprocess."""
    global _proc
    if _proc and _proc.poll() is None:
        _proc.terminate()
    return jsonify({"status": "paused"})


@app.route("/api/thresholds", methods=["POST"])
def set_thresholds():
    """Set MAX_BUY_PRICE and PROFIT_TARGET_CENTS env vars (inherited by next subprocess start)."""
    data = request.get_json() or {}
    max_buy = data.get("max_buy_price")
    profit  = data.get("profit_target_cents")
    if max_buy is not None:
        os.environ["MAX_BUY_PRICE"] = str(int(max_buy))
    if profit is not None:
        os.environ["PROFIT_TARGET_CENTS"] = str(int(profit))
    return jsonify({
        "status": "ok",
        "max_buy_price": int(os.environ.get("MAX_BUY_PRICE", "60")),
        "profit_target_cents": int(os.environ.get("PROFIT_TARGET_CENTS", "7")),
    })


@app.route("/api/status", methods=["GET"])
def get_status():
    running = bool(_proc and _proc.poll() is None)
    return jsonify({
        "running": running,
        "configured": _configured,
        "max_buy_price": int(os.environ.get("MAX_BUY_PRICE", "60")),
        "profit_target_cents": int(os.environ.get("PROFIT_TARGET_CENTS", "7")),
    })


@app.route("/api/logs", methods=["GET"])
def stream_logs():
    """Server-Sent Events stream of main.py output."""
    def generate():
        # Send existing buffered lines first
        with _log_lock:
            snapshot = list(_log_lines)
        for line in snapshot:
            yield f"data: {line}\n\n"

        # Then tail new lines as they arrive
        seen = len(snapshot)
        import time
        while True:
            with _log_lock:
                current = list(_log_lines)
            for line in current[seen:]:
                yield f"data: {line}\n\n"
            seen = len(current)
            time.sleep(0.25)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(port=8000, debug=True, threaded=True)
