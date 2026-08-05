#!/usr/bin/env python3
"""Telecharge l historique de cloture d une valeur et l ecrit dans <label>.csv.

Trois points de vigilance, tous constates en production le 05/08/2026 :

  1. Yahoo renvoie regulierement une seance avec close = null (trous observes
     les 31/07 et 04/08/2026 sur ASML.AS). L ancienne version se contentait de
     jeter ces lignes, ce qui trouait definitivement le fichier. On va desormais
     chercher la valeur dans les bougies horaires de la journee concernee.

  2. Les horodatages sont en UTC. Sans le decalage de la place (gmtoffset), une
     seance peut etre datee du mauvais jour. Sans consequence sur Euronext, mais
     faux d un jour sur les places asiatiques.

  3. Le fichier existant n est plus ecrase aveuglement : il est fusionne. Si
     Yahoo perd une valeur qu on avait deja, on la conserve.
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


def resolve_symbol(entry):
    entry = entry.strip()
    is_isin = len(entry) == 12 and entry[:2].isalpha() and entry.isalnum()
    if not is_isin:
        return entry, entry  # c'est deja un symbole Yahoo
    q = urllib.parse.quote(entry)
    data = http_json(f"https://query1.finance.yahoo.com/v1/finance/search?q={q}")
    quotes = data.get("quotes", [])
    if not quotes:
        raise SystemExit(f"Aucun symbole trouve pour l'ISIN {entry}")
    return quotes[0].get("symbol"), entry


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
    return [(jour_de(t, off), c) for t, c in zip(ts, closes)]


def main():
    entry = os.environ.get("ISIN", "").strip() or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not entry:
        raise SystemExit("Aucun ISIN/symbole fourni")
    symbol, label = resolve_symbol(entry)
    fname = f"{label}.csv"

    connu  = lire_csv(fname)
    brut   = fetch_history(symbol)
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

    print(f"{fname} ecrit : {len(lignes)} lignes (symbole Yahoo {symbol})")
    print(f"  seances a close nulle : {len(trous)}  |  reconstituees : {repares}  |  toujours absentes : {len(perdus)}")
    if perdus:
        apercu = ", ".join(perdus[:15]) + (" ..." if len(perdus) > 15 else "")
        print(f"  ATTENTION seances manquantes dans {fname} : {apercu}")


if __name__ == "__main__":
    main()
