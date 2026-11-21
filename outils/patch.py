# -*- coding: utf-8 -*-
"""Patch par remplacements (21/11/2026) : alerte emergents seulement au-dessus de
la cible + 3 points, comme pour l Europe (le retard se rattrape par les
versements). Applique par le workflow patch.yml ; chaque texte doit etre trouve
une seule fois, sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"veille.py": [
("""    # Alerte emergents seulement quand l ecart sort de la bande (la veille il y etait),
    # et le jour du versement ; sinon l ecart figure dans le rapport.
    hors_bande = abs(part_em - cib["emergents"]) > cib["emergents_bande"]
    try:
        em_veille = float(veille.get("part_em"))
        hors_bande_veille = abs(em_veille - cib["emergents"]) > cib["emergents_bande"]
    except (TypeError, ValueError):
        hors_bande_veille = False
    if hors_bande and (not hors_bande_veille or est_jour_versement(cib)):
        alertes.append("Emergents a %s de la poche actions (cible %s)." % (pc(part_em), pc(cib["emergents"])))""",
"""    # Comme pour l Europe : un retard sur la cible se rattrape par les versements et
    # figure dans le rapport ; alerte seulement si la cible est depassee de plus de
    # la bande (il faut alors reduire PAASI dans les versements).
    if part_em > cib["emergents"] + cib["emergents_bande"]:
        alertes.append("Emergents a %s de la poche actions, au-dessus de la cible %s : "
                       "reduire la part de PAASI dans les versements." % (pc(part_em), pc(cib["emergents"])))"""),
],
"regles.md": [
("""  marché mondial (MSCI ACWI). Alerte si l'écart dépasse 3 points.""",
"""  marché mondial (MSCI ACWI). Un retard se rattrape par les versements, sans
  alerte ; alerte seulement si la part dépasse la cible de plus de 3 points."""),
],
"cibles.txt": [
("""emergents_bande  = 0.03   # alerte si l ecart depasse 3 points""",
"""emergents_bande  = 0.03   # alerte seulement si les emergents depassent la cible de plus de 3 points"""),
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
