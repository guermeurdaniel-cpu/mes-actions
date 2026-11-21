# -*- coding: utf-8 -*-
"""Patch par remplacements (21/11/2026) : la courbe du patrimoine garde les lignes
vendues jusqu a leur date de vente (avant, une ligne vendue disparaissait de tout
l historique, alors que ses apports restaient comptes : la courbe « vs argent non
place » plongeait artificiellement). Applique par le workflow patch.yml ; chaque
texte doit etre trouve une seule fois, sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"index.html": [
("""    const cle=sup.cle, q=qtyOf(cle); if(!q) return;""",
"""    const cle=sup.cle, q=qtyOf(cle);
    // Une ligne vendue (quantite nulle aujourd hui) reste dans l historique : qteA()
    // lui donne sa quantite a chaque date, donc sa valeur jusqu a la vente.
    if(!q && !APPORTS.some(function(a){ return a.cle===cle; })) return;"""),
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
