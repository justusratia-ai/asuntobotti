#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Rental watcher -> Telegram
# Ehdot: max_rent (oletus 850), 'keskusta' -heuristiikka (otsikko/osoite)
# Käyttö:
#   export TELEGRAM_BOT_TOKEN=123:ABC...
#   export TELEGRAM_CHAT_ID=123456789
#   python rental_watcher.py --city "Vaasa" --max 850 --interval 600
# Voit myös ajaa kertaluonteisesti ilman --interval ja laittaa cronin hoitamaan ajastuksen.
# Huom: sivustojen DOM voi muuttua -> selektoreita voi pitää päivittää. Käytä maltillista pyyntöväliä (pause).

import os
import re
import json
import time
import argparse
from dataclasses import dataclass
from typing import List, Optional, Dict
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; RentalWatcher/1.1; +https://example.com)"
}

CENTER_PATTERNS = re.compile(
    r"\bkeskus(?:ta|ssa)?\b|\bcentrum\b|\bcenter\b", re.I
)

@dataclass
class Listing:
    source: str
    title: str
    price_eur: Optional[int]
    address: str
    city: str
    url: str

def parse_price_to_int(txt: str) -> Optional[int]:
    if not txt:
        return None
    cleaned = re.sub(r"[^\d]", "", txt)
    return int(cleaned) if cleaned.isdigit() else None

def looks_centerish(title: str, address: str) -> bool:
    hay = f"{title} {address}".lower()
    return bool(CENTER_PATTERNS.search(hay))

# ------------- Scrapers -------------
def search_vuokraovi(city: str, max_rent: int) -> List[Listing]:
    url = (
        "https://www.vuokraovi.com/vuokra-asunnot/"
        f"{requests.utils.quote(city)}?yhteensa=1&jarjestys=0&vuokraMax={max_rent}"
    )
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    out = []
    cards = soup.select("[data-automation-id='search-result-card'], .card-item, article")
    for c in cards:
        title_el = c.select_one("[data-automation-id='card-title'], h2, .heading, .card__title")
        title = title_el.get_text(strip=True) if title_el else "Ilmoitus"
        link_el = c.select_one("a[href*='/vuokra-asunto/']")
        url_full = ("https://www.vuokraovi.com" + link_el["href"]) if link_el and link_el["href"].startswith("/") else (link_el["href"] if link_el else "")
        price_el = c.select_one("[data-automation-id='card-price'], .price, .card__price")
        price = parse_price_to_int(price_el.get_text() if price_el else "")
        addr_el = c.select_one("[data-automation-id='card-address'], .address, .card__address, .location")
        address = addr_el.get_text(" ", strip=True) if addr_el else ""
        if url_full and (price is None or price <= max_rent):
            out.append(Listing("Vuokraovi", title, price, address, city, url_full))
    return out

def search_oikotie(city: str, max_rent: int) -> List[Listing]:
    url = (
        "https://asunnot.oikotie.fi/vuokrattavat-asunnot?"
        f"locations={requests.utils.quote(city)}&price[max]={max_rent}&cardType=100"
    )
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    out = []
    cards = soup.select("[data-testid*='card'], article, a[href*='/vuokrattavat-asunnot/']")
    for c in cards:
        link_el = c if (c.name == "a" and c.get("href")) else c.select_one("a[href*='/vuokrattavat-asunnot/']")
        url_path = link_el["href"] if link_el and link_el.get("href") else ""
        url_full = "https://asunnot.oikotie.fi" + url_path if url_path.startswith("/") else url_path

        title_el = c.select_one("[data-testid*='title'], h2, .styles__Title, .title")
        title = title_el.get_text(strip=True) if title_el else "Ilmoitus"

        price_el = c.select_one("[data-testid*='price'], .price, .styles__Price")
        price = parse_price_to_int(price_el.get_text() if price_el else "")

        addr_el = c.select_one("[data-testid*='address'], .address, .styles__Address")
        address = addr_el.get_text(" ", strip=True) if addr_el else ""

        if url_full and (price is None or price <= max_rent):
            out.append(Listing("Oikotie", title, price, address, city, url_full))
    return out

def search_qasa(city: str, max_rent: int) -> List[Listing]:
    url = (
        "https://www.qasa.fi/fi/asunnot?"
        f"city={requests.utils.quote(city)}&maxRent={max_rent}&type=apartment"
    )
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    out = []
    cards = soup.select("a[href*='/fi/asunto/'], article, [data-testid*='listing']")
    for c in cards:
        link_el = c if (c.name == "a" and c.get("href")) else c.select_one("a[href*='/fi/asunto/']")
        url_path = link_el["href"] if link_el and link_el.get("href") else ""
        url_full = "https://www.qasa.fi" + url_path if url_path.startswith("/") else url_path

        title_el = c.select_one("h2, [data-testid*='title'], .title")
        title = title_el.get_text(strip=True) if title_el else "Ilmoitus"

        price_el = c.select_one(string=re.compile("€|eur", re.I))
        price_text = price_el if isinstance(price_el, str) else (price_el.get_text() if price_el else "")
        price = parse_price_to_int(price_text)

        addr_el = c.select_one("[data-testid*='address'], .address, .location")
        address = addr_el.get_text(" ", strip=True) if addr_el else ""

        if url_full and (price is None or price <= max_rent):
            out.append(Listing("Qasa", title, price, address, city, url_full))
    return out

# ------------- Core -------------
def fetch_all(city: str, max_rent: int, pause: float) -> List[Listing]:
    all_listings: List[Listing] = []
    for fn in (search_vuokraovi, search_oikotie, search_qasa):
        try:
            all_listings.extend(fn(city, max_rent))
        except Exception as e:
            print(f"[WARN] {fn.__name__} failed: {e}")
        time.sleep(pause)
    filtered = [l for l in all_listings if looks_centerish(l.title, l.address)]
    return filtered if filtered else all_listings

def load_seen(path: str) -> Dict[str, float]:
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"[WARN] failed to load {path}: {e}")
        return {}

def save_seen(path: str, seen: Dict[str, float]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        import json
        json.dump(seen, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def tg_send_message(token: str, chat_id: str, text: str, disable_web_page_preview: bool = False):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": disable_web_page_preview,
    }
    r = requests.post(url, json=payload, timeout=20)
    if not r.ok:
        raise RuntimeError(f"Telegram error {r.status_code}: {r.text}")

def fmt_listing(l: Listing) -> str:
    price_txt = f"{l.price_eur} €/kk" if l.price_eur is not None else "—"
    center_flag = " (keskusta?)" if looks_centerish(l.title, l.address) else ""
    title = re.sub(r"\s+", " ", l.title).strip()
    addr = re.sub(r"\s+", " ", l.address).strip()
    return (
        f"🔔 <b>Uusi vuokra-asunto</b> {center_flag}\n"
        f"🏷️ {title}\n"
        f"📍 {addr or l.city}\n"
        f"💶 {price_txt}\n"
        f"🔗 {l.url}\n"
        f"🏠 Lähde: {l.source}"
    )

def key_for(l: Listing) -> str:
    return f"{l.source}|{l.url}"

def run_once(city: str, max_rent: int, pause: float, seen_path: str,
             token: str, chat_id: str, max_push: int = 8) -> int:
    listings = fetch_all(city, max_rent, pause)
    seen = load_seen(seen_path)
    new_items = [l for l in listings if key_for(l) not in seen]

    sent = 0
    for l in new_items[:max_push]:
        try:
            tg_send_message(token, chat_id, fmt_listing(l), disable_web_page_preview=False)
            seen[key_for(l)] = time.time()
            sent += 1
            time.sleep(0.8)
        except Exception as e:
            print(f"[WARN] Telegram send failed: {e}")

    if new_items[max_push:]:
        try:
            more = len(new_items) - max_push
            tg_send_message(
                token, chat_id,
                f"ℹ️ {more} lisäosumaa jäi lähettämättä tässä ajossa. Ne merkitty nähdyiksi.",
                disable_web_page_preview=True
            )
            for l in new_items[max_push:]:
                seen[key_for(l)] = time.time()
        except Exception as e:
            print(f"[WARN] Telegram summary failed: {e}")

    save_seen(seen_path, seen)
    print(f"[INFO] Sent {sent} new notifications. Total seen={len(seen)}")
    return sent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--city", default=os.getenv("CITY", "Vaasa"))
    ap.add_argument("--max", type=int, default=int(os.getenv("MAX_RENT", "850")))
    ap.add_argument("--pause", type=float, default=1.5, help="Viive eri sivujen pyyntöjen väliin (s).")
    ap.add_argument("--seen", default="seen_listings.json", help="Nähtyjen listausten polku.")
    ap.add_argument("--interval", type=int, default=0, help="Sekunteina; jos >0, loopataan näin usein.")
    ap.add_argument("--max-push", type=int, default=8, help="Maksimi ilmoituksia per ajo.")
    args = ap.parse_args()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise SystemExit("Aseta TELEGRAM_BOT_TOKEN ja TELEGRAM_CHAT_ID ympäristömuuttujiksi.")

    if args.interval > 0:
        while True:
            try:
                run_once(args.city, args.max, args.pause, args.seen, token, chat_id, args.max_push)
            except Exception as e:
                print(f"[ERROR] run_once failed: {e}")
            time.sleep(args.interval)
    else:
        run_once(args.city, args.max, args.pause, args.seen, token, chat_id, args.max_push)

if __name__ == "__main__":
    main()
