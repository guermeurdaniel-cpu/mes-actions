# -*- coding: utf-8 -*-
"""Patch par remplacements (25/11/2026, soir) : retour du message Telegram de la veille.
Depuis le 24/11, le seul lancement fiable de veille.py est celui que declenche la
tache du soir (commit de rapports/demande.txt), et ce lancement n envoyait rien sur
Telegram : la liste des bonnes affaires n arrivait plus.
1. Un lancement par commit envoie le message s il vient de la demande du soir
   (message de commit commencant par « demande de veille »), sauf si un lancement
   planifie a deja ecrit le rapport du jour (et donc deja envoye le message).
   Une simple modification du script n envoie toujours rien.
2. Message plus lisible : puces, titres en gras, legende du tableau raccourcie.
Applique par le workflow patch.yml ; chaque texte doit etre trouve une seule fois,
sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"veille.py": [
("""    alertes, sections, ko = [], [], []
""",
"""    alertes, sections, ko = [], [], []
    # Rapport du jour deja ecrit par un lancement planifie (qui a envoye le message) ?
    rapport_deja_fait = os.path.exists(os.path.join(DOSSIER, "veille-%s.md" % JOUR))
"""),
("""    if os.environ.get("GITHUB_EVENT_NAME") == "push":
        print("  Telegram : lancement par commit, pas de message")
        return
""",
"""    if os.environ.get("GITHUB_EVENT_NAME") == "push":
        if not lancement_du_soir():
            print("  Telegram : lancement par modification du depot, pas de message")
            return
        if rapport_deja_fait:
            print("  Telegram : deja envoye par le lancement planifie du jour")
            return
"""),
("""def telegram(texte, html_mode=False):""",
"""def lancement_du_soir():
    \"\"\"Vrai si le workflow a ete declenche par la demande de la tache du soir
    (commit de rapports/demande.txt, message « demande de veille ... »).\"\"\"
    try:
        with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
            ev = json.load(f)
        return (ev.get("head_commit") or {}).get("message", "").startswith("demande de veille")
    except Exception:
        return False


def telegram(texte, html_mode=False):"""),
("""        blocs = ["<b>Veille du %s</b>" % AUJ.strftime("%d/%m/%Y")]
        if alertes:
            blocs.append("\\n".join("- " + e(a) for a in alertes))
        if tab:
            blocs.append("<b>Bonnes affaires achetables</b> (delai d un mois atteint)\\n<pre>"
                         + e("\\n".join(tab)) + "</pre>\\n"
                         "Baisse depuis le plus haut 6 mois. PER : cours / benefice des 12 derniers "
                         "mois. PERa : cours / benefice attendu. Div : dividende annuel / cours.")
        blocs.append(e("Actions %s / defensif %s (cible %s). MSCI World %s du plus haut."
                       % (pc(part_act), pc(1 - part_act), pc(cible),
                          pc(-baisse_monde if baisse_monde is not None else None, True))))""",
"""        blocs = ["<b>\\U0001F4CB Veille du %s</b>" % AUJ.strftime("%d/%m/%Y")]
        blocs.append(e("Actions %s / cible %s\\nMSCI World %s du plus haut"
                       % (pc(part_act), pc(cible),
                          pc(-baisse_monde if baisse_monde is not None else None, True))))
        if alertes:
            blocs.append("<b>Alertes</b>\\n" + "\\n".join("\\u2022 " + e(a) for a in alertes))
        if tab:
            blocs.append("<b>\\U0001F50E Bonnes affaires achetables</b>\\n<pre>"
                         + e("\\n".join(tab)) + "</pre>\\n"
                         "<i>Baisse sur 6 mois, PER, PER attendu, dividende</i>")"""),
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
