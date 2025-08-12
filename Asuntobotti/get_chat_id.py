#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import requests

token = os.getenv("TELEGRAM_BOT_TOKEN")
if not token:
    raise SystemExit("Aseta ensin TELEGRAM_BOT_TOKEN ympäristömuuttuja.")

url = f"https://api.telegram.org/bot{token}/getUpdates"
r = requests.get(url, timeout=20)
r.raise_for_status()
data = r.json()

if not data.get("ok"):
    raise SystemExit(f"Virhe: {data}")

results = data.get("result", [])
if not results:
    print("Ei viestejä. Avaa bottisi chat, paina Start ja lähetä viesti. Aja skripti uudelleen.")
else:
    printed = set()
    for update in results:
        chat = None
        if isinstance(update, dict):
            chat = (update.get("message", {}) or {}).get("chat") or (update.get("channel_post", {}) or {}).get("chat")
        if chat:
            cid = chat.get("id")
            if cid in printed:
                continue
            printed.add(cid)
            name = chat.get("title") or chat.get("first_name") or chat.get("username") or "Chat"
            print(f"Nimi: {name}")
            print(f"Chat ID: {cid}")
            print("-" * 30)
