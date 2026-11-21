# -*- coding: utf-8 -*-
"""Patch par remplacements (21/11/2026) : versement mensuel pilote par reservoirs
sur 5 ans avec modulation 0 a 3 fois la base (regles.md §4, cibles.txt), et baisse
depuis le plus haut 1 an des trois ETF dans le rapport de veille. Applique par le
workflow patch.yml ; chaque texte doit etre trouve une seule fois, sinon aucun
fichier n est ecrit."""
import sys

PATCHS = {
"veille.py": [
("""SYM_MONDE, SYM_EM, SYM_MP, SYM_CHANGE = "WPEA.PA", "PAASI.PA", "EXXY.DE", "EURUSD=X\"""",
"""SYM_MONDE, SYM_EM, SYM_MP, SYM_CHANGE = "WPEA.PA", "PAASI.PA", "EXXY.DE", "EURUSD=X"
SYM_EU = "PCEU.PA\""""),
("""    for sym in (SYM_MONDE, SYM_EM, SYM_MP, SYM_CHANGE):""",
"""    for sym in (SYM_MONDE, SYM_EM, SYM_MP, SYM_CHANGE, SYM_EU):"""),
("""    r.append("- MSCI World (WPEA) : %s depuis son plus haut 1 an" % pc(-baisse_monde if baisse_monde is not None else None, True))""",
"""    r.append("- MSCI World (WPEA) : %s depuis son plus haut 1 an" % pc(-baisse_monde if baisse_monde is not None else None, True))
    def depuis_haut(pts):
        return (pts[-1][1] / max(v for _, v in pts) - 1) if pts else None
    def sur_un_an(pts):
        return perf(pts, 250) if pts else None
    r.append("- Les trois ETF du versement, ecart au plus haut 1 an / performance 1 an : "
             "MSCI World (WPEA) %s / %s ; MSCI Europe (PCEU) %s / %s ; Asie emergente (PAASI) %s / %s"
             % (pc(depuis_haut(series[SYM_MONDE]), True), pc(sur_un_an(series[SYM_MONDE]), True),
                pc(depuis_haut(series[SYM_EU]), True), pc(sur_un_an(series[SYM_EU]), True),
                pc(depuis_haut(series[SYM_EM]), True), pc(sur_un_an(series[SYM_EM]), True)))"""),
],
"cibles.txt": [
("""# Repartition par defaut du versement (regles.md §4), en euros
versement_wpea     = 290
versement_pceu     = 200  # tant que l Europe est sous sa cible
versement_paasi    = 160  # tant que les emergents sont sous leur cible ; ensuite 80
versement_defensif = 350""",
"""# Reservoirs (regles.md §4) : cibles Europe et emergents a atteindre en
# horizon_mois versements a partir de decembre 2026 (soit fin 2031)
horizon_mois       = 60
modulation_max     = 3    # chaque reservoir recoit entre 0 et 3 fois sa base
# Bases du versement, calculees le 21/11/2026 (recalculees a chaque revue), en euros
versement_wpea     = 130
versement_pceu     = 370
versement_paasi    = 150
versement_defensif = 350  # assurance vie : fonds euros + Euro Liquidity, UC entre 32 et 35 %"""),
],
"regles.md": [
("""Répartition par défaut à partir du 5 décembre 2026 (validée le 21/11/2026) :

| Support | Montant |
|---|---|
| WPEA (MSCI World) | 290 € |
| PCEU (MSCI Europe) | 200 € |
| PAASI (Asie émergente) | 160 € |
| Défensif (assurance vie : fonds euros, en gardant 32 à 35 % de monétaire) | 350 € |

- PAASI à 160 € tant que les émergents sont sous 10 % de la poche actions ;
  ensuite 80 €, les 80 € libérés allant à WPEA.
- PCEU à 200 € tant que l'Europe, toutes sources, est sous 30 % de la poche
  actions ; ensuite le montant qui la maintient à 30 % (environ 100 €), le
  reste allant à WPEA.
- Si la répartition s'écarte de la cible, la revue mensuelle oriente tout ou
  partie du versement vers le côté en retard.
- La poche « bonnes affaires » est alimentée seulement au moment d'un achat
  validé, à partir de la part actions du versement.""",
"""Le versement remplit des **réservoirs** sur un horizon de **5 ans** (60
versements, de décembre 2026 à fin 2031), avec une modulation mensuelle selon
l'actualité. Décidé le 21/11/2026.

**Défensif : 350 €**, uniquement dans l'assurance vie, répartis entre le fonds
euros et Amundi Euro Liquidity de façon à garder les unités de compte entre
32 et 35 % du contrat (bonus du fonds euros à partir de 30 %). Ce montant ne
change que si la répartition 65/35 sort de sa bande ou si un palier de forte
baisse est déclenché (§2).

**Actions : 650 €**, entre trois réservoirs et les bonnes affaires.

1. **Base de chaque réservoir** : le montant mensuel qui, répété jusqu'à fin
   2031, amène l'Europe à 30 % et les émergents à 10 % d'une poche actions
   qui grossit de 650 € par mois (effet de marché ignoré). La part européenne
   des achats de WPEA (15 %) et les achats d'actions européennes comptent pour
   l'Europe. WPEA reçoit le reste. Recalculée à chaque revue sur les montants
   réels : un mois où un réservoir reçoit plus réduit sa base des mois
   suivants, et inversement. Bases au 21/11/2026 : PCEU 370 €, PAASI 150 €,
   WPEA 130 €.
2. **Modulation** : chaque mois, chaque réservoir reçoit **entre 0 et 3 fois
   sa base**, dans la limite des 650 €, selon la baisse depuis le plus haut,
   la valorisation et l'actualité. Exemple : l'Europe perd 15 % pendant que le
   monde est stable, PCEU peut recevoir jusqu'à 650 € ce mois-là.
3. **Bonnes affaires** : au plus un achat par mois, entre 500 et 1 000 €, pris
   sur la part actions du mois, seulement si l'analyse conclut à une vraie
   occasion (§5) et dans les plafonds.
4. **Mémoire et contrôle** : chaque revue est consignée dans
   suivi/plan-versements.md (écarts, bases, décision, justification, et ce
   qu'aurait donné la base sans modulation), puis comparée aux achats réels de
   apports.csv. À 12 puis 24 mois, la performance des décisions modulées est
   comparée à celle des bases seules ; si la modulation ne fait pas mieux, on
   revient aux bases."""),
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
