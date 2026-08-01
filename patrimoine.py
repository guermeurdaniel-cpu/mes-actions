# -*- coding: utf-8 -*-
"""
patrimoine.py — Enregistre chaque jour la valeur REELLE du patrimoine global
dans patrimoine.json (liste de {date, valeur}).

Sources :
  - supports.txt : catalogue des valeurs (intitule, cle, source de cotation)
  - apports.csv  : journal des apports, d ou sont deduites les quantites detenues
  - index.html   : uniquement le montant du fonds euros
  - nav.json   : dernieres VL des fonds (Amundi, Carmignac, ODDO)
  - Yahoo Finance (cote serveur, pas de CORS) : WPEA.PA, PAASI.PA, ASML.AS, CC4.PA

Une entree par date ; si le script tourne plusieurs fois le meme jour,
l'entree du jour est ecrasee (la derniere valeur gagne).
"""

import json
import re
import datetime

from curl_cffi import requests as creq

import supports as supports_mod

# Les valeurs cotees viennent du catalogue : rien a tenir a jour ici.
SUPPORTS = supports_mod.lire()
YAHOO_SYMBOLS = supports_mod.cotes(SUPPORTS)
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1d&interval=1d"


def lire_fonds_euros(chemin="index.html"):
    """Le fonds euros n a pas de parts : son montant est saisi dans index.html."""
    with open(chemin, "r", encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"const\s+FONDS_EUROS\s*=\s*([\d.]+)", html)
    if not m:
        raise RuntimeError("FONDS_EUROS introuvable dans index.html")
    return float(m.group(1))


def nombre_fr(txt):
    """Convertit '39,07' ou '39.07' en float. Chaine vide -> None."""
    t = (txt or "").strip().replace("\u00a0", "").replace(" ", "").replace("EUR", "").replace("\u20ac", "")
    if not t:
        return None
    return float(t.replace(",", "."))


def lire_apports(intitules, chemin="apports.csv"):
    """Somme les quantites du journal des apports, par cle de support.

    Format : date ; intitule ; quantite ; prix   (# = commentaire)
    Une quantite negative est une vente : elle diminue simplement la quantite.
    """
    quantites = {}
    with open(chemin, "r", encoding="utf-8-sig") as f:
        for num, brut in enumerate(f, start=1):
            ligne = brut.strip()
            if not ligne or ligne.startswith("#"):
                continue
            champs = ligne.split(";")
            if len(champs) < 3:
                raise RuntimeError("apports.csv ligne %d : moins de 3 champs" % num)
            nom = champs[1].strip()
            qte = nombre_fr(champs[2])
            if nom not in intitules:
                raise RuntimeError("apports.csv ligne %d : intitule absent de supports.txt : '%s'" % (num, nom))
            if qte is None:
                raise RuntimeError("apports.csv ligne %d : quantite absente" % num)
            cle = intitules[nom]
            quantites[cle] = quantites.get(cle, 0.0) + qte
    return quantites


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
    quantites = lire_apports(supports_mod.par_intitule(SUPPORTS))
    fonds_euros = lire_fonds_euros()

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
