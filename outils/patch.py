# -*- coding: utf-8 -*-
"""Patch par remplacements (28/11/2026, 2e passe) : patrimoine.py deduit les frais
de gestion trimestriels des unites de compte (champ frais de supports.txt, calcul
supports.frais_trimestriels) dans lire_apports et lire_mouvements, donc aussi
dans veille.py. Meme resultat que la page.
Applique par le workflow patch.yml ; chaque texte doit etre trouve une seule fois,
sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"patrimoine.py": [
('def lire_apports(intitules, chemin="apports.csv"):\n    """Somme les quantites du journal des apports, par cle de support.\n\n    Format : date ; intitule ; quantite ; prix   (# = commentaire)\n    Une quantite negative est une vente : elle diminue simplement la quantite.\n    """\n    quantites = {}\n    with open(chemin, "r", encoding="utf-8-sig") as f:\n        for num, brut in enumerate(f, start=1):\n            ligne = brut.strip()\n            if not ligne or ligne.startswith("#"):\n                continue\n            champs = ligne.split(";")\n            if len(champs) < 3:\n                raise RuntimeError("apports.csv ligne %d : moins de 3 champs" % num)\n            nom = champs[1].strip()\n            qte = nombre_fr(champs[2])\n            if nom not in intitules:\n                raise RuntimeError("apports.csv ligne %d : intitule absent de supports.txt : \'%s\'" % (num, nom))\n            if qte is None:\n                raise RuntimeError("apports.csv ligne %d : quantite absente" % num)\n            cle = intitules[nom]\n            quantites[cle] = quantites.get(cle, 0.0) + qte\n    return quantites\n\n\ndef lire_mouvements(intitules, chemin="apports.csv"):\n    """Mouvements dates par cle : {cle: [(date, quantite), ...]}. Sert aux livrets,\n    dont la valeur depend des dates de versement (regle des quinzaines)."""\n    mvts = {}\n    with open(chemin, "r", encoding="utf-8-sig") as f:\n        for brut in f:\n            ligne = brut.strip()\n            if not ligne or ligne.startswith("#"):\n                continue\n            champs = ligne.split(";")\n            nom = champs[1].strip() if len(champs) > 1 else ""\n            qte = nombre_fr(champs[2]) if len(champs) > 2 else None\n            if nom in intitules and qte is not None:\n                mvts.setdefault(intitules[nom], []).append((champs[0].strip(), qte))\n    return mvts\n\n\n',
 'def _avec_frais(mvts, jusqua=None):\n    """Ajoute aux mouvements {cle: [(date, qte), ...]} les prelevements trimestriels\n    de frais des supports qui ont un champ frais dans supports.txt."""\n    jusqua = jusqua or datetime.date.today().isoformat()\n    for s in SUPPORTS:\n        if s.get("frais") and s["cle"] in mvts:\n            mvts[s["cle"]] = mvts[s["cle"]] + supports_mod.frais_trimestriels(\n                s["frais"], mvts[s["cle"]], jusqua)\n    return mvts\n\n\ndef lire_apports(intitules, chemin="apports.csv"):\n    """Somme les quantites du journal des apports, par cle de support.\n\n    Format : date ; intitule ; quantite ; prix   (# = commentaire)\n    Une quantite negative est une vente : elle diminue simplement la quantite.\n    Les frais trimestriels des unites de compte (champ frais de supports.txt)\n    sont deduits automatiquement.\n    """\n    mvts = {}\n    with open(chemin, "r", encoding="utf-8-sig") as f:\n        for num, brut in enumerate(f, start=1):\n            ligne = brut.strip()\n            if not ligne or ligne.startswith("#"):\n                continue\n            champs = ligne.split(";")\n            if len(champs) < 3:\n                raise RuntimeError("apports.csv ligne %d : moins de 3 champs" % num)\n            nom = champs[1].strip()\n            qte = nombre_fr(champs[2])\n            if nom not in intitules:\n                raise RuntimeError("apports.csv ligne %d : intitule absent de supports.txt : \'%s\'" % (num, nom))\n            if qte is None:\n                raise RuntimeError("apports.csv ligne %d : quantite absente" % num)\n            mvts.setdefault(intitules[nom], []).append((champs[0].strip(), qte))\n    quantites = {}\n    for cle, l in _avec_frais(mvts).items():\n        q = sum(x for _, x in l)\n        quantites[cle] = 0.0 if abs(q) < 1e-6 else q\n    return quantites\n\n\ndef lire_mouvements(intitules, chemin="apports.csv"):\n    """Mouvements dates par cle : {cle: [(date, quantite), ...]}. Sert aux livrets,\n    dont la valeur depend des dates de versement (regle des quinzaines).\n    Frais trimestriels des unites de compte inclus."""\n    mvts = {}\n    with open(chemin, "r", encoding="utf-8-sig") as f:\n        for brut in f:\n            ligne = brut.strip()\n            if not ligne or ligne.startswith("#"):\n                continue\n            champs = ligne.split(";")\n            nom = champs[1].strip() if len(champs) > 1 else ""\n            qte = nombre_fr(champs[2]) if len(champs) > 2 else None\n            if nom in intitules and qte is not None:\n                mvts.setdefault(intitules[nom], []).append((champs[0].strip(), qte))\n    return _avec_frais(mvts)\n\n\n'),
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
