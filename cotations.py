#!/usr/bin/env python3
import os, sys, json, csv, datetime, urllib.request, urllib.parse

def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

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

def fetch_history(symbol, rng="5y"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?range={rng}&interval=1d"
    res = http_json(url)["chart"]["result"][0]
    ts = res["timestamp"]
    closes = res["indicators"]["quote"][0]["close"]
    rows = []
    for t, c in zip(ts, closes):
        if c is not None:
            d = datetime.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")
            rows.append((d, round(c, 4)))
    return rows

def main():
    entry = os.environ.get("ISIN", "").strip() or (sys.argv[1] if len(sys.argv) > 1 else "")
    if not entry:
        raise SystemExit("Aucun ISIN/symbole fourni")
    symbol, label = resolve_symbol(entry)
    rows = fetch_history(symbol)
    fname = f"{label}.csv"
    with open(fname, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Date", "Close"])
        w.writerows(rows)
    print(f"{fname} cree : {len(rows)} lignes (symbole Yahoo {symbol})")

if __name__ == "__main__":
    main()
