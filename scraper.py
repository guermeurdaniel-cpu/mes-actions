#!/usr/bin/env python3
# Recuperation des VL sans navigateur (plus de Playwright), via curl_cffi (empreinte TLS Chrome) :
#  - Fonds PEG (QS...) : API JSON interne Amundi EE  /product-services/fdr/share/v3/full/{ISIN}
#                        -> champ lastNav.value (nombre) et lastNav.date (ISO AAAA-MM-JJ)
#  - Fonds AV  (FR...) : page abcbourse.com, VL lue dans le HTML servi.
# Run attendu : quelques secondes (aucun Chromium a installer, aucun rendu a attendre).
import json, re, os, datetime, time
# curl_cffi remplace requests : meme API, mais reproduit l'empreinte TLS/JA3/HTTP2 de Chrome.
# Necessaire car l'API Amundi filtre par empreinte TLS (405 avec requests, 200 en navigateur).
from curl_cffi import requests

FONDS = [
    { "isin":"QS0009080175", "label":"Amundi Actions Internationales ESR - F", "category":"PEG", "source":"amundi-api" },
    { "isin":"QS0009080746", "label":"Amundi Label Equilibre ESR - F",         "category":"PEG", "source":"amundi-api" },
    { "isin":"QS0009080720", "label":"Amundi Label Monetaire ESR - F",         "category":"PEG", "source":"amundi-api" },
    { "isin":"FR0011408798", "label":"Amundi Euro Liquidity-Rated", "category":"AV", "source":"abcbourse",
      "url":"https://www.abcbourse.com/opcvm/amundi-euro-liquidity-rated-sri-e-c_sFR0011408798" },
    { "isin":"FR0010149120", "label":"Carmignac Securite AW EUR", "category":"AV", "source":"abcbourse",
      "url":"https://www.abcbourse.com/opcvm/carmignac-securite-aw-eur-acc_sFR0010149120" },
]
OUT = "nav.json"; HIST = "history.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")

def parse_num(s):
    s = s.strip().replace('\u00a0','').replace(' ','').replace('€','')
    if ',' in s and '.' in s:
        s = (s.replace('.','').replace(',','.')) if s.rfind(',')>s.rfind('.') else s.replace(',','')
    elif ',' in s:
        s = s.replace(',','.')
    return float(s)

def http_get(url, headers, tries=3, timeout=30):
    for t in range(1, tries+1):
        try:
            r = requests.get(url, headers=headers, timeout=timeout, impersonate="chrome")
            if r.status_code == 200:
                return r
            print(f"[http] {url} -> HTTP {r.status_code} (essai {t}/{tries})")
        except Exception as e:
            print(f"[http] {url} erreur: {e} (essai {t}/{tries})")
        time.sleep(4)
    return None

# --- PEG : API JSON Amundi EE ------------------------------------------------
def find_last_nav(obj):
    # Cherche un objet {value, date, ...} porte par une cle contenant "nav" (ex. lastNav).
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, dict) and "nav" in k.lower() and "value" in v and "date" in v:
                return v
        for v in obj.values():
            r = find_last_nav(v)
            if r: return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_last_nav(v)
            if r: return r
    return None

def scrape_amundi_api(isin):
    url = f"https://www.amundi-ee.com/product-services/fdr/share/v3/full/{isin}"
    headers = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "fr-FR,fr;q=0.9",
        "Referer": f"https://www.amundi-ee.com/epargnant/product/view/{isin}",
    }
    print(f"[amundi] {url}")
    r = http_get(url, headers)
    if not r:
        return None, None
    try:
        data = r.json()
    except Exception as e:
        print(f"[amundi]   JSON invalide: {e}")
        return None, None
    nav = find_last_nav(data)
    if nav and nav.get("value") is not None:
        try:
            value = float(nav["value"])
        except Exception:
            print(f"[amundi]   value non numerique: {nav.get('value')}")
            return None, None
        nav_date = nav.get("date")  # deja au format ISO AAAA-MM-JJ
        print(f"[amundi]   value={value} date={nav_date}")
        return value, nav_date
    print(f"[amundi]   lastNav/value introuvable dans le JSON")
    return None, None

# --- AV : page HTML abcbourse ------------------------------------------------
def html_to_text(html):
    html = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', html)
    txt = re.sub(r'(?s)<[^>]+>', ' ', html)
    txt = (txt.replace('&nbsp;', '\u00a0').replace('&euro;', '€')
              .replace('&#8364;', '€').replace('&#160;', '\u00a0'))
    return re.sub(r'[ \t]+', ' ', txt)

def scrape_abcbourse(url):
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9",
    }
    print(f"[abcbourse] {url}")
    r = http_get(url, headers)
    if not r:
        return None, None
    text = html_to_text(r.text)
    value = None; nav_date = None
    d = re.search(r'Date valorisation\s*:?\s*(\d{2}/\d{2}/\d{4})', text)
    if d:
        jj, mm, aaaa = d.group(1).split("/"); nav_date = f"{aaaa}-{mm}-{jj}"
    head = text.split("Date valorisation")[0] if "Date valorisation" in text else text
    m = re.search(r'([\d\u00a0 ]+,\d{2,4})\s*EUR', head)
    if m:
        value = parse_num(m.group(1))
    if value is None:
        print(f"[abcbourse]   VL introuvable")
    else:
        print(f"[abcbourse]   value={value} date={nav_date}")
    return value, nav_date

# --- IO ----------------------------------------------------------------------
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
    for f in FONDS:
        if f["source"]=="amundi-api": value,nav_date=scrape_amundi_api(f["isin"])
        else:                         value,nav_date=scrape_abcbourse(f["url"])

        if value is not None:
            date = nav_date or datetime.date.today().isoformat()
            results[f["isin"]]={"isin":f["isin"],"label":f["label"],"category":f["category"],
                "value":value,"currency":"EUR","date":date,"status":"ok"}
            merge_history(history,f["isin"],date,value)
        else:
            old_val, old_date = last_known(history, f["isin"])
            if old_val is not None:
                print(f"[robot]   -> reprise derniere VL connue : {old_val} ({old_date})")
                results[f["isin"]]={"isin":f["isin"],"label":f["label"],"category":f["category"],
                    "value":old_val,"currency":"EUR","date":old_date,"status":"ancien"}
            else:
                results[f["isin"]]={"isin":f["isin"],"label":f["label"],"category":f["category"],
                    "value":None,"currency":"EUR","date":datetime.date.today().isoformat(),"status":"not_found"}

        print(f"[robot] {f['isin']} -> {results[f['isin']]}")
    with open(OUT,"w",encoding="utf-8") as fh: json.dump(results,fh,ensure_ascii=False,indent=2)
    with open(HIST,"w",encoding="utf-8") as fh: json.dump(history,fh,ensure_ascii=False,indent=2)
    print(f"[robot] Ecrit {OUT} et {HIST}")

if __name__=="__main__": main()
