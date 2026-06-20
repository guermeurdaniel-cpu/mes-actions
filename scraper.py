#!/usr/bin/env python3
import json, re, sys, datetime
from playwright.sync_api import sync_playwright

ISIN = "QS0009080175"
URL = f"https://www.amundi-ee.com/epargnant/product/view/{ISIN}"
OUT = "nav.json"

def extract_numbers(text):
    cands = re.findall(r'(\d{1,3}(?:[ \u00a0]\d{3})*[.,]\d{2,4}|\d{1,5}[.,]\d{2,4})', text or "")
    out = []
    for c in cands:
        try:
            v = float(c.replace('\u00a0', '').replace(' ', '').replace(',', '.'))
            if 1 < v < 100000:
                out.append(v)
        except ValueError:
            pass
    return out

def deep_find_nav(obj, found):
    KEYS = ("nav", "vl", "valeurliquidative", "value", "price", "shareprice", "lastnav")
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower().replace("_", "").replace(" ", "")
            if any(key in kl for key in KEYS) and isinstance(v, (int, float, str)):
                try:
                    fv = float(str(v).replace(",", "."))
                    if 1 < fv < 100000:
                        found.append((k, fv))
                except ValueError:
                    pass
            deep_find_nav(v, found)
    elif isinstance(obj, list):
        for it in obj:
            deep_find_nav(it, found)

def main():
    captured = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        def on_response(resp):
            try:
                ct = resp.headers.get("content-type", "")
                url = resp.url
                if "json" in ct or any(s in url.lower() for s in ("nav", "price", "product", "fund", ISIN.lower())):
                    body = resp.text()
                    if body and len(body) < 2000000:
                        captured.append({"url": url, "ct": ct, "body": body})
            except Exception:
                pass
        page.on("response", on_response)
        print(f"[robot] Ouverture de {URL}")
        try:
            page.goto(URL, wait_until="domcontentloaded", timeout=90000)
        except Exception as e:
            print(f"[robot] goto a renvoye : {e} (on continue quand meme)")
        page.wait_for_timeout(8000)
        try:
            page.screenshot(path="debug.png", full_page=True)
            print("[robot] capture d'ecran debug.png prise")
        except Exception:
            pass
        page_text = page.inner_text("body")
        browser.close()

    nav = None; source = None
    print(f"[robot] {len(captured)} reponse(s) reseau candidate(s).")
    for c in captured:
        print(f"[robot]  - {c['url'][:120]} ({c['ct']})")
        try:
            data = json.loads(c["body"])
        except Exception:
            continue
        found = []
        deep_find_nav(data, found)
        if found:
            print(f"[robot]    -> cles VL trouvees : {found[:5]}")
            if nav is None:
                nav = found[0][1]; source = c["url"]

    if nav is None:
        nums = extract_numbers(page_text)
        print(f"[robot] Fallback texte. Nombres plausibles : {nums[:10]}")
        print("[robot] --- extrait texte page ---")
        print((page_text or "")[:1500])
        print("[robot] --- fin extrait ---")
        if nums:
            nav = nums[0]; source = "page_text"

    result = {
        "isin": ISIN, "value": nav, "currency": "EUR",
        "date": datetime.date.today().isoformat(),
        "source": source, "status": "ok" if nav is not None else "not_found",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[robot] Ecrit {OUT} : {result}")

if __name__ == "__main__":
    main()
