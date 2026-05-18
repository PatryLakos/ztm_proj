"""
ZTM Proxy — sspróbuje oba endpointysss, zwraca dsssane w ujednoliconej formie. Używa tokena z env var ZTM_TOKEN.
"""
from flask import Flask, jsonify, request
import requests
import os

app = Flask(__name__)

API_TOKEN = os.environ.get("ZTM_TOKEN", "")

# Stary endpoint (GET)
OLD_URL = "https://api.um.warszawa.pl/api/action/dbtimetable_get/"
OLD_RES = "e923fa0e-d96c-43f9-ae6e-60518c9f3238"

# Nowy endpoint (POST)
NEW_URL = "https://dane.um.warszawa.pl/api/action/get_ztm_odjazdy_linii_z_przystanku"

def try_new_api(stop_id, stop_nr, line):
    resp = requests.post(
        NEW_URL,
        json={"busstopId": stop_id, "busstopNr": stop_nr, "line": line},
        headers={"Authorization": API_TOKEN, "Content-Type": "application/json"},
        timeout=8
    )
    resp.raise_for_status()
    data = resp.json()
    entries = data if isinstance(data, list) else []
    deps = []
    for entry in entries[:8]:
        kv = {item["key"]: item["value"] for item in entry if item.get("value")}
        if "czas" in kv:
            deps.append({
                "line": line,
                "time": kv["czas"][:5],
                "dir":  kv.get("kierunek", "?")[:20]
            })
    return deps

def try_old_api(stop_id, stop_nr, line):
    resp = requests.get(
        OLD_URL,
        params={
            "id":         OLD_RES,
            "apikey":     API_TOKEN,
            "busstopId":  stop_id,
            "busstopNr":  stop_nr,
            "line":       line,
        },
        timeout=8
    )
    resp.raise_for_status()
    data = resp.json()
    result = data.get("result", [])
    deps = []
    for entry in result[:8]:
        kv = {item["key"]: item["value"] for item in entry.get("values", []) if item.get("value")}
        if "czas" in kv:
            deps.append({
                "line": line,
                "time": kv["czas"][:5],
                "dir":  kv.get("kierunek", "?")[:20]
            })
    return deps

@app.route("/ztm")
def ztm():
    stop_id = request.args.get("stopId", "7009")
    stop_nr = request.args.get("stopNr", "01")
    line    = request.args.get("line",   "151")

    # Próbuj nowe API, fallback na stare
    for attempt, fn in [("new", try_new_api), ("old", try_old_api)]:
        try:
            deps = fn(stop_id, stop_nr, line)
            return jsonify({"ok": True, "deps": deps, "source": attempt})
        except Exception as e:
            last_err = str(e)

    return jsonify({"ok": False, "error": last_err}), 500

@app.route("/")
def health():
    return jsonify({"status": "ok", "token_set": bool(API_TOKEN)})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)