# -*- coding: utf-8 -*-
"""
patrimoine.py — Enregistre chaque jour la valeur REELLE du patrimoine global
dans patrimoine.json (liste de {date, valeur}).

Sources :
  - index.html : QUANTITES + FONDS_EUROS (source de verite unique, editee a la main)
  - nav.json   : dernieres VL des fonds (Amundi, Carmignac, ODDO)
  - Yahoo Finance (cote serveur, pas de CORS) : WPEA.PA, PAASI.PA, ASML.AS, CC4.PA

Une entree par date ; si le script tourne plusieurs fois le meme jour,
l'entree du jour est ecrasee (la derniere valeur gagne).
"""

import json
import re
import datetime

from curl_cffi import requests as creq

YAHOO_SYMBOLS = ["WPEA.PA", "PAASI.PA", "ASML.AS", "CC4.PA"]
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1d&interval=1d"


def lire_quantites_et_fonds_euros(chemin="index.html"):
    """Extrait QUANTITES (dict) et FONDS_EUROS (float) depuis index.html."""
    with open(chemin, "r", encoding="utf-8") as f:
        html = f.read()

    m = re.search(r"const\s+QUANTITES\s*=\s*\{(.*?)\};", html, re.S)
    if not m:
        raise RuntimeError("Bloc QUANTITES introuvable dans index.html")
    bloc = m.group(1)

    quantites = {}
    for cle, expr in re.findall(r'"([^"]+)"\s*:\s*([^,\n]+)', bloc):
        expr = expr.split("//")[0].strip().rstrip(",")
        if not re.fullmatch(r"[\d.\s+\-*/()]+", expr):
            raise RuntimeError("Expression non numerique pour %s : %s" % (cle, expr))
        quantites[cle] = float(eval(expr, {"__builtins__": {}}, {}))

    m2 = re.search(r"const\s+FONDS_EUROS\s*=\s*([\d.]+)", html)
    if not m2:
        raise RuntimeError("FONDS_EUROS introuvable dans index.html")
    fonds_euros = float(m2.group(1))

    return quantites, fonds_euros


def prix_yahoo(sym):
    """Dernier cours Yahoo pour un symbole, ou None si echec."""
    try:
        r = creq.get(YAHOO_URL.format(sym=sym), impersonate="chrome", timeout=20)
        meta = r.json()["chart"]["result"][0]["meta"]
        p = meta.get("regularMarketPrice")
        return float(p) if p is not None else None
    except Exception as e:
        print("  Yahoo KO %s : %s" % (sym, e))
        return None


def main():
    quantites, fonds_euros = lire_quantites_et_fonds_euros()

    with open("nav.json", "r", encoding="utf-8") as f:
        nav = json.load(f)

    total = fonds_euros
    manquants = []

    for isin, q in quantites.items():
        if isin in YAHOO_SYMBOLS:
            continue  # traite plus bas via Yahoo
        f_ = nav.get(isin)
        if f_ and f_.get("value") is not None:
            total += q * float(f_["value"])
            print("  %s : %s x %s" % (isin, q, f_["value"]))
        else:
            manquants.append(isin)

    for sym in YAHOO_SYMBOLS:
        q = quantites.get(sym, 0)
        if not q:
            continue
        p = prix_yahoo(sym)
        if p is not None:
            total += q * p
            print("  %s : %s x %s" % (sym, q, p))
        else:
            # repli : derniere valeur connue dans nav.json si presente
            f_ = nav.get(sym)
            if f_ and f_.get("value") is not None:
                total += q * float(f_["value"])
                print("  %s (repli nav.json) : %s x %s" % (sym, q, f_["value"]))
            else:
                manquants.append(sym)

    if manquants:
        print("ATTENTION lignes sans valeur (exclues du total) : %s" % ", ".join(manquants))

    aujourdhui = datetime.date.today().isoformat()
    total = round(total, 2)
    print("Patrimoine total %s : %s EUR" % (aujourdhui, total))

    try:
        with open("patrimoine.json", "r", encoding="utf-8") as f:
            histo = json.load(f)
        if not isinstance(histo, list):
            histo = []
    except Exception:
        histo = []

    histo = [e for e in histo if e.get("date") != aujourdhui]
    histo.append({"date": aujourdhui, "valeur": total})
    histo.sort(key=lambda e: e["date"])

    with open("patrimoine.json", "w", encoding="utf-8") as f:
        json.dump(histo, f, ensure_ascii=False, indent=1)
    print("patrimoine.json mis a jour (%d entrees)." % len(histo))


if __name__ == "__main__":
    main()
