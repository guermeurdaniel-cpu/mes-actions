#!/usr/bin/env python3
import json, re, os, datetime
from playwright.sync_api import sync_playwright

# category : "PEG" (epargne salariale Amundi) ou "AV" (assurance vie)
# source   : "amundi-ee" ou "easybourse"
FONDS = [
    { "isin":"QS0009080175", "label":"Amundi Actions Internationales ESR - F", "category":"PEG", "source":"amundi-ee" },
    { "isin":"QS0009080746", "label":"Amundi Label Equilibre ESR - F",         "category":"PEG", "source":"amundi-ee" },
    { "isin":"QS0009080720", "label":"Amundi Label Monetaire ESR - F",         "category":"PEG", "source":"amundi-ee" },
    { "isin":"FR0011408798", "label":"Amundi Euro Liquidity-Rated Responsible","category":"AV",  "source":"easybourse" },
    { "isin":"FR0010149120", "label":"Carmignac Securite AW EUR",              "category":"AV",  "source":"easybourse" },
    { "isin":"LU1681039647", "label":"Amundi Euro Corporate SRI ETF",          "category":"AV",  "source":"easybourse" },
]
OUT = "nav.json"
HIST = "history.json"

def parse_num(s):
    s = s.strip().replace('\u00a0','').replace(' ','').replace('€','')
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.','').replace(',','.')
        else:
            s = s.replace(',','')
    elif ',' in s:
        s = s.replace(',','.')
    return float(s)

def scrape_amundi(page, isin):
    url = f"https://www.amundi-ee.com/epargnant/product/view/{isin}"
    print(f"[robot] (PEG) {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
    except Exception as e:
        print(f"[robot]   goto: {e}")
    page.wait_for_timeout(8000)
    text = page.inner_text("body")
    value=None; nav_date=None
    m = re.search(r'Valeur Liquidative\s*\(C\)\s*:\s*([\d \u00a0]+[.,]\d{2,4})', text)
    if m: value = parse_num(m.group(1))
    d = re.search(r'Date des donn[ée]es\s*:\s*(\d{2}/\d{2}/\d{4})', text)
    if d:
        jj,mm,aaaa = d.group(1).split("/"); nav_date = f"{aaaa}-{mm}-{jj}"
    if value is None:
        print(f"[robot]   VL introuvable, extrait:"); print((text or '')[:1000])
    return value, nav_date

def scrape_easybourse(page, isin):
    url = f"https://www.easybourse.com/opcvm/{isin}/"
    print(f"[robot] (AV) {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
    except Exception as e:
        print(f"[robot]   goto: {e}")
    page.wait_for_timeout(6000)
    text = page.inner_text("body")
    value=None; nav_date=None
    m = re.search(r'VL\s*:?\s*([0-9][0-9\s.,\u00a0]*?)\s*€', text)
    if m: value = parse_num(m.group(1))
    d = re.search(r'Date\s*VL\s*:?\s*(\d{2}/\d{2}/\d{4})', text)
    if d:
        jj,mm,aaaa = d.group(1).split("/"); nav_date = f"{aaaa}-{mm}-{jj}"
    if value is None:
        print(f"[robot]   VL introuvable, extrait:"); print((text or '')[:1000])
    return value, nav_date

def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    return default

def merge_history(history, isin, date, value):
    arr = history.get(isin, [])
    for e in arr:
        if e["date"] == date:
            e["value"] = value; break
    else:
        arr.append({"date":date, "value":value})
    arr.sort(key=lambda e: e["date"])
    history[isin] = arr[-400:]
    return history

def main():
    results = {}
    history = load_json(HIST, {})
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for f in FONDS:
            if f["source"] == "amundi-ee":
                value, nav_date = scrape_amundi(page, f["isin"])
            else:
                value, nav_date = scrape_easybourse(page, f["isin"])
            date = nav_date or datetime.date.today().isoformat()
            results[f["isin"]] = {
                "isin":f["isin"], "label":f["label"], "category":f["category"],
                "value":value, "currency":"EUR", "date":date,
                "status":"ok" if value is not None else "not_found",
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
