# -*- coding: utf-8 -*-
"""
realises.py — Synthese des ventes et arbitrages : plus ou moins-values realisees.

Relance par .github/workflows/realises.yml a chaque modification de apports.csv
(saisie d un mouvement dans la page, ou modification a la main). Ecrit
realises.csv, lu par la page « Mes valeurs » pour afficher, dans l en-tete, les
gains et pertes en cours (lignes detenues) et deja realises (ventes).

Methode du prix de revient moyen (PRU), la meme que la page : pour chaque vente
(quantite negative avec un prix), plus-value = quantite vendue x (prix de vente
- PRU a la date de la vente). Le PRU est la moyenne ponderee des achats de prix
connu dates au plus tard du jour de la vente ; une vente ne le modifie pas.
"""

import datetime

ENTETE = """# =============================================================================
#  PLUS ET MOINS-VALUES REALISEES (fichier genere par realises.py, ne pas editer)
# =============================================================================
#  Une ligne par vente ou sortie d arbitrage du journal apports.csv.
#  plus_value = quantite vendue x (prix de vente - prix de revient moyen a la date)
#  Mis a jour le %s. Total realise : %s EUR.
# -----------------------------------------------------------------------------
date;support;quantite_vendue;prix_vente;prix_revient;montant_vente;plus_value
"""


def nombre(txt):
    t = (txt or "").strip().replace(" ", "").replace(" ", "").replace("EUR", "").replace("€", "")
    return float(t.replace(",", ".")) if t else None


def lire_journal(chemin="apports.csv"):
    lignes = []
    with open(chemin, encoding="utf-8-sig") as f:
        for brut in f:
            l = brut.strip()
            if not l or l.startswith("#"):
                continue
            c = l.split(";")
            if len(c) < 3:
                continue
            q = nombre(c[2])
            p = nombre(c[3]) if len(c) > 3 else None
            if q is None:
                continue
            lignes.append((c[0].strip(), c[1].strip(), q, p))
    return lignes


def realises(journal):
    sorties = []
    for date, nom, q, p in sorted(journal):
        if q >= 0 or p is None:
            continue
        achats = [(qa, pa) for d, n, qa, pa in journal
                  if n == nom and qa > 0 and pa is not None and d <= date]
        qte = sum(qa for qa, _ in achats)
        pru = sum(qa * pa for qa, pa in achats) / qte if qte else None
        vendu = -q
        pv = vendu * (p - pru) if pru is not None else 0.0
        sorties.append((date, nom, vendu, p, pru, vendu * p, pv))
    return sorties


def main():
    s = realises(lire_journal())
    total = sum(x[6] for x in s)
    def f(x, n=2):
        return "" if x is None else ("%.*f" % (n, x))
    texte = ENTETE % (datetime.date.today().strftime("%d/%m/%Y"), f(total))
    for date, nom, vendu, p, pru, mt, pv in s:
        texte += ";".join([date, nom, f(vendu, 6), f(p, 4), f(pru, 4), f(mt), f(pv)]) + "\n"
    with open("realises.csv", "w", encoding="utf-8") as out:
        out.write(texte)
    print(texte)


if __name__ == "__main__":
    main()
