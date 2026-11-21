# -*- coding: utf-8 -*-
"""Patch par remplacements (21/11/2026) : la page n affiche plus les supports dont
la quantite detenue est nulle (lignes vendues, support pas encore achete). Ils
restent dans le catalogue et dans la liste de l onglet Saisie. Applique par le
workflow patch.yml ; chaque texte doit etre trouve une seule fois, sinon aucun
fichier n est ecrit."""
import sys

PATCHS = {
"index.html": [
("""    env.keys.forEach(function(cle){
      const row=document.createElement("div"); row.className="row";
      if(estFixe(cle)){""",
"""    env.keys.forEach(function(cle){
      if(Math.abs(qtyOf(cle))<1e-9) return;   // support vendu ou pas encore achete : masque
      const row=document.createElement("div"); row.className="row";
      if(estFixe(cle)){"""),
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
