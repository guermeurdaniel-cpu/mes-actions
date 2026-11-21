# -*- coding: utf-8 -*-
"""Patch par remplacements (21/11/2026) : arbitrage de l assurance vie vers Amundi
Euro Liquidity (regles.md §8). Montants estimes aux dernieres valeurs connues, a
corriger avec l avis d operation BoursoVie. Applique par le workflow patch.yml ;
chaque texte doit etre trouve une seule fois, sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"apports.csv": [
("""2026-06-16;ODDO Global Target 2029;0.2715;110.29
""",
"""2026-06-16;ODDO Global Target 2029;0.2715;110.29
# Arbitrage du 21/11/2026 vers Amundi Euro Liquidity (regles.md §8). Montants
# ESTIMES aux dernieres valeurs connues : a remplacer par ceux de l avis
# d operation BoursoVie (nombre de parts et valeur de la part).
2026-11-21;Carmignac Securite;-1.6917;1917.50
2026-11-21;ETF Euro Corporate SRI;-14.3676;226.00
2026-11-21;ODDO Global Target 2029;-0.2715;110.08
2026-11-21;Amundi Euro Liquidity;0.59192;11016.29
"""),
],
}

nouveaux = {}
for fichier, remplacements in PATCHS.items():
    s = open(fichier, encoding="utf-8").read()
    for ancien, nouveau in remplacements:
        n = s.count(ancien)
        if n != 1:
            print("ECHEC %s : texte trouve %d fois : %r" % (fichier, n, ancien[:80]))
            sys.exit(1)
        s = s.replace(ancien, nouveau)
    nouveaux[fichier] = s
for fichier, s in nouveaux.items():
    open(fichier, "w", encoding="utf-8").write(s)
    print("%s : patch applique" % fichier)
