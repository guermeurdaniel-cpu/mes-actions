#!/usr/bin/env python3
import json, re, os, datetime
from playwright.sync_api import sync_playwright

FONDS = [
    { "isin": "QS0009080175", "label": "Amundi Actions Internationales ESR - F" },
    { "isin": "QS0009080746", "label": "Amundi Label Equilibre ESR - F" },
    { "isin": "QS0009080720", "label": "Amundi Label Monetaire ESR - F" },
]
OUT = "nav.json"
HIST = "history.json"

def scrape_one(page, isin):
    url = f"https://www.amundi-ee.com/epargnant/product/view/{isin}"
    print(f"[robot] Ouverture de {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
    except Exception as e:
        print(f"[robot] goto a renvoye : {e} (on continue)")
    page.wait_for_timeout(8000)
    text = page.inner_text("body")

    value = None; nav_date = None
    m = re.search(r'Valeur Liquidative\s*\(C\)\s*:\s*([\d \u00a0]+[.,]\d{2,4})', text)
    if m:
        value = float(m.group(1).replace('\u00a0','').replace(' ','').replace(',', '.'))
    d = re.search(r'Date des donn[ée]es\s*:\s*(\d{2}/\d{2}/\d{4})', text)
    if d:
        jj, mm, aaaa = d.group(1).split("/")
        nav_date = f"{aaaa}-{mm}-{jj}"
    if value is None:
        print(f"[robot] VL non trouvee pour {isin}, extrait :")
        print((text or "")[:1200])
    return value, nav_date

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def merge_history(history, isin, date, value):
    arr = history.get(isin, [])
    for e in arr:
        if e["date"] == date:
            e["value"] = value
            break
    else:
        arr.append({"date": date, "value": value})
    arr.sort(key=lambda e: e["date"])
    history[isin] = arr[-400:]   # on garde ~400 jours, large pour usage futur
    return history

def main():
    results = {}
    history = load_json(HIST, {})

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for f in FONDS:
            value, nav_date = scrape_one(page, f["isin"])
            date = nav_date or datetime.date.today().isoformat()
            results[f["isin"]] = {
                "isin": f["isin"], "label": f["label"],
                "value": value, "currency": "EUR",
                "date": date,
                "status": "ok" if value is not None else "not_found",
            }
            print(f"[robot] {f['isin']} -> {results[f['isin']]}")
            if value is not None:
                merge_history(history, f["isin"], date, value)
        browser.close()

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
    with open(HIST, "w", encoding="utf-8") as fh:
        json.dump(history, fh, ensure_ascii=False, indent=2)
    print(f"[robot] Ecrit {OUT} et {HIST}")

if __name__ == "__main__":
    main()
