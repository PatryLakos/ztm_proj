"""
ZTM Proxy — mini serwer Flask
Przyjmuje GET od ESP32, robi POST do dane.um.warszawa.pl
Wdrożenie: Render.com (darmowy plan)
"""
from flask import Flask, jsonify, request
import requests
import os

app = Flask(__name__)

API_URL   = "https://dane.um.warszawa.pl/api/action/get_ztm_odjazdy_linii_z_przystanku"
API_TOKEN = os.environ.get("ZTM_TOKEN", "TWOJ_TOKEN")  # ustaw w Render jako env var

@app.route("/ztm")
def ztm():
    stop_id  = request.args.get("stopId",  "7009")
    stop_nr  = request.args.get("stopNr",  "01")
    line     = request.args.get("line",    "151")

    try:
        resp = requests.post(
            API_URL,
            json={"busstopId": stop_id, "busstopNr": stop_nr, "line": line},
            headers={"Authorization": API_TOKEN, "Content-Type": "application/json"},
            timeout=8
        )
        data = resp.json()

        # Wyciągnij czas i kierunek, zwróć uproszczony JSON
        departures = []
        entries = data if isinstance(data, list) else data.get("result", [])
        for entry in entries[:6]:
            kv = {item["key"]: item["value"] for item in entry if item.get("value")}
            if "czas" in kv:
                departures.append({
                    "line": line,
                    "time": kv["czas"][:5],      # "HH:MM"
                    "dir":  kv.get("kierunek", "?")[:20]
                })

        return jsonify({"ok": True, "deps": departures})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/")
def health():
    return "ZTM Proxy dziala!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
