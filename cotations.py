#!/usr/bin/env python3
"""Telecharge l historique de cloture d une valeur et l ecrit dans <label>.csv.

Quatre points de vigilance, constates en production :

  1. Yahoo renvoie regulierement une seance avec close = null (trous observes
     les 31/07 et 04/08/2026 sur ASML.AS). L ancienne version se contentait de
     jeter ces lignes, ce qui trouait definitivement le fichier. On va desormais
     chercher la valeur dans les bougies horaires de la journee concernee.

  2. Les horodatages sont en UTC. Sans le decalage de la place (gmtoffset), une
     seance peut etre datee du mauvais jour. Sans consequence sur Euronext, mais
     faux d un jour sur les places asiatiques.

  3. Le fichier existant n est plus ecrase aveuglement : il est fusionne. Si
     Yahoo perd une valeur qu on avait deja, on la conserve.

  4. La recherche par ISIN rend plusieurs lignes de cotation du meme titre, dans
     un ordre arbitraire. Prendre la premiere donnait un fichier vide quand elle
     n a pas de serie (constate sur LU3038520774 le 08/09/2026). On les essaie
     donc toutes, places europeennes d abord, et on garde la premiere qui rend
     vraiment des seances.
"""
import os, sys, json, csv, time, datetime, urllib.request, urllib.parse

UA          = "Mozilla/5.0"
CHART       = "https://query1.finance.yahoo.com/v8/finance/chart/"
MAX_REPARS  = 40          # plafond de requetes de rattrapage, par securite
JOURS_60M   = 700         # profondeur ou Yahoo sert encore des bougies horaires


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def jour_de(sec, off):
    """Date de seance : horodatage UTC ramene a l heure locale de la place."""
    return datetime.datetime.fromtimestamp(sec + off, datetime.timezone.utc).strftime("%Y-%m-%d")


def serie(res):
    meta   = res["meta"]
    off    = meta.get("gmtoffset") or 0
    ts     = res.get("timestamp") or []
    closes = (res.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    return off, ts, closes


def candidats_isin(entry):
    """Symboles Yahoo proposes pour un ISIN, places europeennes d abord.

    L ordre de la recherche Yahoo n est pas garanti : il peut mettre en tete une
    ligne fantome sans aucune seance ou, pire, une cotation dans une autre
    devise que l euro. On reclasse donc par suffixe de place.
    """
    q = urllib.parse.quote(entry)
    data = http_json(f"https://query1.finance.yahoo.com/v1/finance/search?q={q}")
    syms = [d.get("symbol") for d in data.get("quotes", []) if d.get("symbol")]
    ordre = [".PA", ".AS", ".BR", ".LS", ".DE", ".MI", ".F", ".SW", ".L"]
    def rang(s):
        for i, suf in enumerate(ordre):
            if s.endswith(suf):
                return i
        return len(ordre)
    return sorted(dict.fromkeys(syms), key=rang)


def resolve(entry):
    """Retourne (symbole Yahoo, libelle du fichier, historique brut, devise).

    Pour un ISIN, on essaie les candidats l un apres l autre et on garde le
    premier qui rend vraiment des seances. L historique est ramene ici pour ne
    pas le retelecharger ensuite.
    """
    entry = entry.strip()
    is_isin = len(entry) == 12 and entry[:2].isalpha() and entry.isalnum()
    if not is_isin:
        brut, devise = fetch_history(entry)
        return entry, entry, brut, devise

    candidats = candidats_isin(entry)
    if not candidats:
        raise SystemExit(f"Aucun symbole trouve pour l'ISIN {entry}")
    print(f"Candidats pour {entry} : {', '.join(candidats)}")

    journal = []
    for sym in candidats[:8]:
        try:
            brut, devise = fetch_history(sym)
        except Exception as e:
            journal.append(f"{sym} : erreur ({e})")
            continue
        utiles = sum(1 for _, c in brut if c is not None)
        journal.append(f"{sym} : {utiles} seances, {devise or '?'}")
        if utiles:
            print(f"Retenu : {sym} ({utiles} seances, {devise})")
            return sym, entry, brut, devise
        time.sleep(0.3)

    raise SystemExit("Aucune serie exploitable pour l'ISIN {} :\n  {}"
                     .format(entry, "\n  ".join(journal)))


def lire_csv(fname):
    """Historique deja enregistre, pour ne rien perdre en cas de regression Yahoo."""
    connu = {}
    if not os.path.exists(fname):
        return connu
    try:
        with open(fname, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                d, c = row.get("Date"), row.get("Close")
                if d and c not in (None, ""):
                    connu[d] = float(c)
    except Exception as e:
        print(f"  ! {fname} illisible ({e}) : on repart de zero")
    return connu


def cloture_intraday(symbol, jour):
    """Derniere bougie horaire non nulle de la journee demandee."""
    t0 = int(datetime.datetime.strptime(jour, "%Y-%m-%d")
             .replace(tzinfo=datetime.timezone.utc).timestamp())
    url = (f"{CHART}{urllib.parse.quote(symbol)}"
           f"?period1={t0 - 86400}&period2={t0 + 172800}&interval=60m")
    try:
        res = http_json(url)["chart"]["result"][0]
    except Exception as e:
        print(f"  ! rattrapage {jour} impossible ({e})")
        return None
    off, ts, closes = serie(res)
    val = None
    for t, c in zip(ts, closes):
        if c is not None and jour_de(t, off) == jour:
            val = c
    return val


def fetch_history(symbol, rng="5y"):
    res = http_json(f"{CHART}{urllib.parse.quote(symbol)}?range={rng}&interval=1d")["chart"]["result"][0]
    off, ts, closes = serie(res)
    devise = res["meta"].get("currency")
    return [(jour_de(t, off), c) for t, c in zip(ts, closes)], devise


def main():
    entry = os.environ.get("ISIN", "").strip() or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not entry:
        raise SystemExit("Aucun ISIN/symbole fourni")
    symbol, label, brut, devise = resolve(entry)
    fname = f"{label}.csv"

    connu  = lire_csv(fname)
    limite = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(days=JOURS_60M)).strftime("%Y-%m-%d")

    valeurs, trous, repares, perdus = dict(connu), [], 0, []
    for d, c in brut:
        if c is not None:
            valeurs[d] = round(c, 4)
        elif d not in valeurs:
            trous.append(d)

    for d in trous:
        if repares >= MAX_REPARS:
            perdus.append(d)
            continue
        if d < limite:
            perdus.append(d)   # au-dela de la profondeur des bougies horaires
            continue
        v = cloture_intraday(symbol, d)
        time.sleep(0.5)        # on reste courtois avec Yahoo
        if v is None:
            perdus.append(d)
        else:
            valeurs[d] = round(v, 4)
            repares += 1
            print(f"  + {d} reconstitue a {valeurs[d]} (bougies horaires)")

    lignes = sorted(valeurs.items())
    with open(fname, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Close"])
        w.writerows(lignes)

    print(f"{fname} ecrit : {len(lignes)} lignes (symbole Yahoo {symbol}, devise {devise})")
    if devise and devise != "EUR":
        print(f"  ATTENTION la serie n est pas en euros ({devise}) : verifier la place retenue")
    print(f"  seances a close nulle : {len(trous)}  |  reconstituees : {repares}  |  toujours absentes : {len(perdus)}")
    if perdus:
        apercu = ", ".join(perdus[:15]) + (" ..." if len(perdus) > 15 else "")
        print(f"  ATTENTION seances manquantes dans {fname} : {apercu}")


if __name__ == "__main__":
    main()
