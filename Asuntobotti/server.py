# server.py — Render web service + tausta-ajastin
import os, threading, time
from flask import Flask
import rental_watcher as rw  # käyttää repoosi jo tallennettua koodia

app = Flask(__name__)
_started = False

def _loop():
    city = os.getenv("CITY", "Vaasa")
    max_rent = int(os.getenv("MAX_RENT", "850"))
    pause = float(os.getenv("PAUSE", "1.5"))
    interval = int(os.getenv("INTERVAL", "600"))  # sekunteina
    seen_path = os.getenv("SEEN_PATH", "seen_listings.json")
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    max_push = int(os.getenv("MAX_PUSH", "8"))

    while True:
        try:
            rw.run_once(city, max_rent, pause, seen_path, token, chat_id, max_push)
        except Exception as e:
            print("[WARN] loop error:", e, flush=True)
        time.sleep(interval)

@app.route("/")
@app.route("/health")
def health():
    # UptimeRobot tms. voi pingata tätä, jotta ilmainen instanssi pysyy hereillä
    return "ok", 200

def _start_bg_once():
    global _started
    if not _started:
        threading.Thread(target=_loop, daemon=True).start()
        _started = True

_start_bg_once()
