# -*- coding: utf-8 -*-
"""Patch par remplacements (21/11/2026) : les 200 EUR du fonds euros sont le
versement initial du 6 mai 2026, pas un gain. Applique par le workflow patch.yml ;
chaque texte doit etre trouve une seule fois, sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"apports.csv": [
("""2026-05-12;Fonds euros;6600;1
2026-05-20;Fonds euros;11335;1
# Ecart entre la valeur saisie jusqu ici (18 135) et les versements (17 935) :
# a confirmer ; si la valeur reelle est 17 935, supprimer la ligne suivante.
2026-06-16;Fonds euros;200;0
""",
"""2026-05-06;Fonds euros;200;1
2026-05-12;Fonds euros;6600;1
2026-05-20;Fonds euros;11335;1
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
