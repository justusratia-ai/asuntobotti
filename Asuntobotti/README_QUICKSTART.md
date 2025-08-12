# Asuntobotti – pikaohje (macOS)

✅ Tavoite: Saat Telegramiin ilmoituksen aina kun uusi Vaasan keskustan (≤ 850 €/kk) asunto löytyy Vuokraovi/Oikotie/Qasa.

---

## 1) Lataa tämä paketti
- Tallenna `asuntobotti.zip` ja pura se.
- Kansion sisällä on: `rental_watcher.py`, `get_chat_id.py`

## 2) Avaa botti Telegramissa
- Mene @BotFatherilla luomaasi bottiin (esim. @vaasa_asunto_bot)
- Paina **Start** ja lähetä sille “Hei”

## 3) Avaa Terminal ja siirry kansioon
```bash
cd ~/Downloads/asuntobotti   # tai mihin purit
```

## 4) Asenna riippuvuudet (kerran)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests beautifulsoup4
```

## 5) Aseta botin token ympäristöön ja hae chat-id
```bash
export TELEGRAM_BOT_TOKEN="PASTA_TÄHÄN_BOT_TOKEN"
python get_chat_id.py
```
- Tulosteessa näet **Chat ID** → kopioi se.

## 6) Aseta chat-id ja käynnistä seuranta
```bash
export TELEGRAM_CHAT_ID="PASTA_TÄHÄN_CHAT_ID"
python rental_watcher.py --city "Vaasa" --max 850 --interval 600
```
- Nyt botti tarkistaa 10 min välein ja lähettää vain uudet osumat.

## 7) (Valinnainen) Käynnistä automaattisesti käynnistyksessä
Lisää tämä `crontab`iin:
```bash
crontab -e
```
Rivi (muokkaa polut):
```bash
*/10 * * * * cd ~/Downloads/asuntobotti && .venv/bin/python rental_watcher.py --city "Vaasa" --max 850 >> rental.log 2>&1
```

---

### Vinkit
- Liikaa ilmoituksia? Lisää sanafilttereitä koodiin tai nosta `--interval`.
- Ei ilmoituksia? Poista `seen_listings.json` testiksi.
- `.py.rtf`-ongelma? Tallenna puhtaana tekstinä `.py`-päätteellä (TextEdit: Format → Make Plain Text).

### Windows-pikahuomio
Käytä PowerShelliä ja komentoja:
```powershell
py -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install requests beautifulsoup4
$env:TELEGRAM_BOT_TOKEN="PASTA"
python get_chat_id.py
$env:TELEGRAM_CHAT_ID="PASTA"
python rental_watcher.py --city "Vaasa" --max 850 --interval 600
```
