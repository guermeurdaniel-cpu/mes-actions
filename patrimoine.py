# -*- coding: utf-8 -*-
"""
patrimoine.py — Enregistre chaque jour la valeur REELLE du patrimoine global
dans patrimoine.json (liste de {date, valeur}).

Sources :
  - apports.csv : journal des apports (source de verite des quantites, editee a la main)
  - index.html  : table LIGNES (intitule -> ISIN/ticker) + FONDS_EUROS
  - nav.json   : dernieres VL des fonds (Amundi, Carmignac, ODDO)
  - Yahoo Finance (cote serveur, pas de CORS) : WPEA.PA, PAASI.PA, ASML.AS, CC4.PA

Une entree par date ; si le script tourne plusieurs fois le meme jour,
l'entree du jour est ecrasee (la derniere valeur gagne).
"""

import json
import re
import datetime

from curl_cffi import requests as creq

YAHOO_SYMBOLS = ["WPEA.PA", "PAASI.PA", "ASML.AS", "CC4.PA", "AIR.PA"]
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1d&interval=1d"


def lire_lignes(chemin="index.html"):
    """Extrait la table LIGNES (intitule lisible -> ISIN ou ticker) depuis index.html."""
    with open(chemin, "r", encoding="utf-8") as f:
        html = f.read()

    m = re.search(r"const\s+LIGNES\s*=\s*\{(.*?)\};", html, re.S)
    if not m:
        raise RuntimeError("Bloc LIGNES introuvable dans index.html")
    lignes = dict(re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', m.group(1)))
    if not lignes:
        raise RuntimeError("Bloc LIGNES vide")
    return lignes


def nombre_fr(txt):
    """Convertit '39,07' ou '39.07' en float. Chaine vide -> None."""
    t = (txt or "").strip().replace("\u00a0", "").replace(" ", "").replace("EUR", "").replace("€", "")
    if not t:
        return None
    return float(t.replace(",", "."))


def lire_apports(lignes, chemin="apports.csv"):
    """Somme les quantites du journal des apports, par ISIN / ticker.

    Format : date ; intitule ; quantite ; prix   (# = commentaire)
    Quantite negative = vente : elle diminue simplement la quantite detenue.
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
            if nom not in lignes:
                raise RuntimeError("apports.csv ligne %d : intitule inconnu '%s'" % (num, nom))
            if qte is None:
                raise RuntimeError("apports.csv ligne %d : quantite absente" % num)
            cle = lignes[nom]
            quantites[cle] = quantites.get(cle, 0.0) + qte
    return quantites


def lire_fonds_euros(chemin="index.html"):
    with open(chemin, "r", encoding="utf-8") as f:
        html = f.read()
    m = re.search(r"const\s+FONDS_EUROS\s*=\s*([\d.]+)", html)
    if not m:
        raise RuntimeError("FONDS_EUROS introuvable dans index.html")
    return float(m.group(1))


def lire_quantites_et_fonds_euros(chemin="index.html"):
    """Quantites detenues (depuis apports.csv) et fonds euros (depuis index.html)."""
    lignes = lire_lignes(chemin)
    return lire_apports(lignes), lire_fonds_euros(chemin)


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
