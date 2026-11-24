# -*- coding: utf-8 -*-
"""Patch par remplacements (24/11/2026, soir) : fiabilite de la veille.
Un lancement planifie du lundi 23/11 est parti dans la nuit (4 h, heure de Paris) :
il a date son rapport du mardi (date UTC du serveur) avec les cours du vendredi,
envoye de fausses alertes, et les lancements du mardi soir n ont rien fait.
1. date du jour = date de Paris ;
2. controle de fraicheur : si la derniere seance de WPEA n est pas celle du jour,
   pas d alerte de mouvement ni de Telegram, et le rapport le dit ;
3. en tete du rapport : date des cours et heure du calcul ;
4. pas de Telegram pour un lancement declenche par un commit (demande de Claude
   via rapports/demande.txt) : la note du soir porte l information.
Applique par le workflow patch.yml ; chaque texte doit etre trouve une seule fois,
sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"veille.py": [
("""import urllib.request
""",
"""import urllib.request
from zoneinfo import ZoneInfo
"""),
("""AUJ = datetime.date.today()
""",
"""# Date de Paris, pas celle du serveur (UTC) : un lancement de GitHub retarde apres
# minuit UTC ne doit pas produire un rapport date du lendemain (incident du 24/11/2026).
AUJ = datetime.datetime.now(ZoneInfo("Europe/Paris")).date()
"""),
("""    # --- 1. Repartition
    lignes, fonds_euros, manquants, _ = valoriser(series)
""",
"""    # --- Fraicheur des cours : la derniere seance de WPEA doit etre celle du jour.
    # Sinon (lancement retarde dans la nuit, jour ferie, Yahoo en retard), les
    # variations du jour sont fausses : pas d alerte de mouvement, pas de Telegram.
    date_cours = series[SYM_MONDE][-1][0] if series[SYM_MONDE] else None
    cours_du_jour = date_cours == AUJ
    if not cours_du_jour:
        ko.append("cours Yahoo du %s, pas du jour : variations du jour non fiables, "
                  "alertes de mouvement et Telegram suspendus"
                  % (date_cours.strftime("%d/%m/%Y") if date_cours else "inconnu"))

    # --- 1. Repartition
    lignes, fonds_euros, manquants, _ = valoriser(series)
"""),
("""        if l["var_jour"] is not None and abs(l["var_jour"]) >= cib["ligne_mouvement_jour"]:""",
"""        if (cours_du_jour and l["var_jour"] is not None
                and abs(l["var_jour"]) >= cib["ligne_mouvement_jour"]):"""),
("""    r.append("# Veille du %s" % AUJ.strftime("%d/%m/%Y"))
    r.append("")
""",
"""    r.append("# Veille du %s" % AUJ.strftime("%d/%m/%Y"))
    r.append("")
    r.append("Cours du %s%s. Calcule le %s (heure de Paris)."
             % (date_cours.strftime("%d/%m/%Y") if date_cours else "inconnu",
                "" if cours_du_jour else " (perimes)",
                datetime.datetime.now(ZoneInfo("Europe/Paris")).strftime("%d/%m/%Y a %H:%M")))
    r.append("")
"""),
("""    tab = tableau_achetables(cand)
    if alertes or tab:""",
"""    # Pas de Telegram si les cours sont perimes, ni pour un lancement declenche par un
    # commit (demande de Claude via rapports/demande.txt, ou modification du script) :
    # dans ce cas la note du soir porte l information.
    tab = tableau_achetables(cand)
    if os.environ.get("GITHUB_EVENT_NAME") == "push":
        print("  Telegram : lancement par commit, pas de message")
        return
    if not cours_du_jour:
        print("  Telegram : cours perimes, pas de message")
        return
    if alertes or tab:"""),
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
