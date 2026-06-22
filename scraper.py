#!/usr/bin/env python3
import json, re, os, datetime
from playwright.sync_api import sync_playwright

FONDS = [
    { "isin":"QS0009080175", "label":"Amundi Actions Internationales ESR - F", "category":"PEG", "source":"amundi-ee" },
    { "isin":"QS0009080746", "label":"Amundi Label Equilibre ESR - F",         "category":"PEG", "source":"amundi-ee" },
    { "isin":"QS0009080720", "label":"Amundi Label Monetaire ESR - F",         "category":"PEG", "source":"amundi-ee" },
    { "isin":"FR0011408798", "label":"Amundi Euro Liquidity-Rated", "category":"AV", "source":"abcbourse",
      "url":"https://www.abcbourse.com/opcvm/amundi-euro-liquidity-rated-sri-e-c_sFR0011408798" },
    { "isin":"FR0010149120", "label":"Carmignac Securite AW EUR", "category":"AV", "source":"abcbourse",
      "url":"https://www.abcbourse.com/opcvm/carmignac-securite-aw-eur-acc_sFR0010149120" },
]
OUT = "nav.json"; HIST = "history.json"

def parse_num(s):
    s = s.strip().replace('\u00a0','').replace(' ','').replace('€','')
    if ',' in s and '.' in s:
        s = (s.replace('.','').replace(',','.')) if s.rfind(',')>s.rfind('.') else s.replace(',','')
    elif ',' in s:
        s = s.replace(',','.')
    return float(s)

def scrape_amundi(page, isin):
    url = f"https://www.amundi-ee.com/epargnant/product/view/{isin}"
    text = ""
    for tentative in range(1, 5):
        print(f"[robot] (PEG) {url}  (essai {tentative}/4)")
        try: page.goto(url, wait_until="domcontentloaded", timeout=90000)
        except Exception as e: print(f"[robot]   goto: {e}")
        try:
            page.wait_for_function(
                "document.body && document.body.innerText.includes('Valeur Liquidative')",
                timeout=25000)
        except Exception:
            print("[robot]   VL pas encore affichee...")
        page.wait_for_timeout(3000)
        text = page.inner_text("body")
        if "Service Unavailable" in text:
            print("[robot]   Amundi indisponible, nouvel essai dans 15s...")
            page.wait_for_timeout(15000); continue
        m = re.search(r'Valeur Liquidative\s*\(C\)\s*:\s*([\d \u00a0]+[.,]\d{2,4})', text)
        if m:
            value = parse_num(m.group(1))
            nav_date = None
            d = re.search(r'Date des donn[ée]es\s*:\s*(\d{2}/\d{2}/\d{4})', text)
            if d:
                jj,mm,aaaa = d.group(1).split("/"); nav_date=f"{aaaa}-{mm}-{jj}"
            return value, nav_date
        print("[robot]   VL introuvable, nouvel essai dans 12s...")
        page.wait_for_timeout(12000)
    print("[robot]   echec apres 4 essais, extrait:"); print((text or '')[:800])
    return None, None

def scrape_abcbourse(page, url):
    print(f"[robot] (AV) {url}")
    try: page.goto(url, wait_until="domcontentloaded", timeout=90000)
    except Exception as e: print(f"[robot]   goto: {e}")
    page.wait_for_timeout(5000)
    text = page.inner_text("body")
    value=None; nav_date=None
    d = re.search(r'Date valorisation\s*:\s*(\d{2}/\d{2}/\d{4})', text)
    if d:
        jj,mm,aaaa = d.group(1).split("/"); nav_date=f"{aaaa}-{mm}-{jj}"
    head = text.split("Date valorisation")[0]
    m = re.search(r'([\d\u00a0 ]+,\d{2,4})\s*EUR', head)
    if m: value = parse_num(m.group(1))
    if value is None:
        print("[robot]   VL introuvable, extrait:"); print((text or '')[:800])
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
        if e["date"]==date: e["value"]=value; break
    else: arr.append({"date":date,"value":value})
    arr.sort(key=lambda e:e["date"]); history[isin]=arr[-400:]
    return history

def last_known(history, isin):
    arr = history.get(isin, [])
    if arr:
        last = arr[-1]
        return last["value"], last["date"]
    return None, None

def main():
    results={}; history=load_json(HIST,{})
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True); page=browser.new_page()
        for f in FONDS:
            if f["source"]=="amundi-ee": value,nav_date=scrape_amundi(page,f["isin"])
            else: value,nav_date=scrape_abcbourse(page,f["url"])

            if value is not None:
                # Succes : valeur du jour
                date = nav_date or datetime.date.today().isoformat()
                results[f["isin"]]={"isin":f["isin"],"label":f["label"],"category":f["category"],
                    "value":value,"currency":"EUR","date":date,"status":"ok"}
                merge_history(history,f["isin"],date,value)
            else:
                # Echec : on reprend la derniere valeur connue dans l'historique
                old_val, old_date = last_known(history, f["isin"])
                if old_val is not None:
                    print(f"[robot]   -> reprise derniere VL connue : {old_val} ({old_date})")
                    results[f["isin"]]={"isin":f["isin"],"label":f["label"],"category":f["category"],
                        "value":old_val,"currency":"EUR","date":old_date,"status":"ancien"}
                else:
                    results[f["isin"]]={"isin":f["isin"],"label":f["label"],"category":f["category"],
                        "value":None,"currency":"EUR","date":datetime.date.today().isoformat(),"status":"not_found"}

            print(f"[robot] {f['isin']} -> {results[f['isin']]}")
        browser.close()
    with open(OUT,"w",encoding="utf-8") as fh: json.dump(results,fh,ensure_ascii=False,indent=2)
    with open(HIST,"w",encoding="utf-8") as fh: json.dump(history,fh,ensure_ascii=False,indent=2)
    print(f"[robot] Ecrit {OUT} et {HIST}")

if __name__=="__main__": main()
