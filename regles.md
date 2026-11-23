# Règles de la stratégie de placement

Version du 21 novembre 2026, modifiée le 23 novembre 2026 (§2, §4, §8 :
contraintes du boost BoursoVie). Document de référence commun au script quotidien
(veille.py) et aux analyses de Claude. Il ne se modifie qu'une fois par an, ou
lors d'une revue mensuelle quand une règle ci-dessous l'autorise. Les valeurs
chiffrées sont dans **cibles.txt** : c'est ce fichier que lisent la page « Mes
valeurs » et le script.

## 1. Principes

- Horizon : retraite vers 2042, environ 16 ans. Pas de besoin de revenu.
- Versement d'environ **1 000 € par mois, le 5 du mois**.
- Le cœur est indiciel (MSCI World). Les actions individuelles restent une
  petite poche encadrée.
- Aucune décision sous le coup de l'émotion : toute décision applique une
  règle écrite ici, et elle est notée dans le journal (notes/).

## 2. Répartition actions / défensif

- **Cible : 65 % actions, 35 % défensif**, sur le patrimoine consolidé
  (PEG + PEA + assurance vie + livrets). Les livrets comptent dans le défensif,
  intérêts compris.
- Alerte si l'écart dépasse **5 points**. Le retour vers la cible se fait
  d'abord par l'orientation des versements mensuels, ensuite seulement par
  arbitrage.

### Paliers de forte baisse

Mesurés sur l'ETF MSCI World du PEA (WPEA) depuis son plus haut sur un an :

| Baisse du MSCI World | Nouvelle cible actions |
|---|---|
| −15 % | 70 % |
| −25 % | 75 % |
| −35 % | 80 % |

- Le passage à un palier s'applique **immédiatement**, sans attendre la revue
  mensuelle : c'est la seule exception à la règle de décision à froid.
- Ordre de mobilisation du défensif :
  1. monétaire de l'assurance vie (Amundi Euro Liquidity) vers des unités de
     compte actions, sans frais ni impôt. Montant limité : après une baisse
     supplémentaire de 25 % des actions, la part d'unités de compte du
     contrat doit rester au-dessus de 30 % (condition du boost, §8) ; sinon,
     transférer moins ;
  2. monétaire du PEG (Label Monétaire ESR) vers Actions Internationales ESR ;
  3. livrets vers le PEA, dans la limite du plafond de versement.
- Retour à 65/35 : progressif, par les versements mensuels, une fois le MSCI
  World revenu à son plus haut. Pas de vente d'actions pour y revenir.

## 3. Poche actions

- **Émergents : 10 % de la poche actions**, via PAASI (Asie émergente
  seulement). C'est la position neutre : les émergents pèsent environ 11 % du
  marché mondial (MSCI ACWI). Un retard se rattrape par les versements, sans
  alerte ; alerte seulement si la part dépasse la cible de plus de 3 points.
- **Europe : 30 % de la poche actions, toutes sources confondues** : part
  européenne du MSCI World (environ 15 %, dans Actions Internationales ESR et
  WPEA), Label Équilibre, actions européennes (Airbus, ASML, Air Liquide,
  Genfit...) et PCEU (MSCI Europe). Le MSCI World est très concentré sur les
  États-Unis (environ 73 %) et la technologie, et mes dépenses futures sont en
  euros. Point de départ le 21/11/2026 : 22,9 %. Décidé le 21/11/2026 : la
  cible est atteinte par les versements sur PCEU en 5 ans environ, plus vite
  si l'Europe recule ou en cas de palier de forte baisse. Pas d'alerte tant
  que l'Europe est sous la cible ; alerte si elle la dépasse de plus de
  3 points.
- **Matières premières (CMSE)** : **0 %** aujourd'hui. Entrée possible par
  paliers de 5 points de la poche actions, décidée en revue mensuelle, si les
  signaux du §6 restent franchis plusieurs semaines.

## 4. Versement mensuel (le 5)

Le versement remplit des **réservoirs** sur un horizon de **5 ans** (60
versements, de décembre 2026 à fin 2031), avec une modulation mensuelle selon
l'actualité. Décidé le 21/11/2026.

**Défensif : 350 €**, uniquement dans l'assurance vie. Pour bénéficier du
boost du fonds euros (§8), chaque versement contient **au moins 30 %
d'unités de compte** (Amundi Euro Liquidity), soit 105 € au moins ; le reste
va au fonds euros. Si la part d'unités de compte du contrat est sous 32 %,
la part d'unités de compte du versement monte jusqu'à 100 % pour revenir
dans la zone 32-35 %. Ce montant ne
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
   revient aux bases.

## 5. Poche « bonnes affaires » (actions individuelles)

- Taille : **10 % de la poche actions au plus**, toutes lignes individuelles
  comprises. Une seule ligne : **5 % du patrimoine au plus**.
- Univers : valeurs éligibles au PEA, de préférence cotées à Paris, Amsterdam ou
  Bruxelles (pas d'ordre minimal). Ailleurs, minimum de 2 500 € chez BoursoBank.
- **Repérage, chaque jour par le script** :
  - baisse d'au moins 25 % depuis le plus haut sur 6 mois ;
  - santé financière : dette nette / EBITDA < 2,5, flux de trésorerie disponible
    positif, marge d'exploitation > 10 %, rentabilité des capitaux propres
    > 10 % ;
  - banques et assurances exclues (ces ratios n'ont pas de sens pour elles).
- **Délai** : au moins **un mois** après le dernier choc (dernière baisse d'au
  moins 10 % en 5 séances), pour laisser passer la baisse qui suit souvent une
  mauvaise nouvelle.
- **Avant d'acheter**, analyse par Claude : actualité, raison de la baisse,
  occasion ou piège. Exclusions : prévisions abaissées de plus de 15 %,
  dividende coupé, perte de parts de marché durable, activité directement
  menacée.
- Rythme : **un achat par mois au plus**. Écrire en trois lignes pourquoi le
  marché a tort.
- Sortie : seulement si la thèse écrite est invalidée, ou si la ligne dépasse
  5 % du patrimoine. Jamais sur une simple variation de cours.
- **Témoin** : chaque achat est comparé à ce qu'aurait donné WPEA à la même
  date. Si la poche fait moins bien que WPEA de plus de 10 points cumulés sur
  3 ans glissants, elle est fermée et reversée dans le cœur.

## 6. Signaux de fond, suivis chaque jour

Ils ne déclenchent rien seuls : ils alimentent la revue mensuelle.

- **Matières premières** : inflation de la zone euro (glissement annuel,
  Eurostat via la BCE) et tendance de l'ETF iShares Diversified Commodity Swap
  sur 6 et 12 mois. Signal allumé si l'inflation dépasse 3 % et que les deux
  tendances sont positives.
- **Émergents** : écart de performance PAASI / WPEA sur 12 mois. Signal allumé
  au-delà de ±10 points ; le change euro/dollar est suivi en complément.
- Un signal doit rester allumé **plusieurs semaines** (20 jours de bourse)
  avant qu'un changement de cible soit proposé, par palier de 5 points au plus.

## 7. Lignes individuelles détenues

| Ligne | Thèse | Conditions de sortie ou d'allègement |
|---|---|---|
| Airbus (PEG) | Carnet de commandes record et montée des cadences de livraison | Cadences durablement révisées en baisse ; ligne au-delà de 5 % du patrimoine. Vigilance : exposition déjà forte au secteur par l'emploi |
| Air Liquide (PEA) | Valeur de fond : croissance régulière, marge en hausse, dividende croissant | Marge en recul deux années de suite ; dividende stable ou en baisse |
| ASML (PEA) | Monopole de la lithographie EUV, demande supérieure à l'offre en 2027-2028 | Baisse durable des commandes ; restrictions d'export vers la Chine aggravées ; ligne au-delà de 5 % du patrimoine |
| Genfit (PEA) | **Spéculatif.** Redevances Iqirvo en forte croissance, nangibotide en phase 2a (données au second semestre 2027), financement assuré jusqu'en 2029 | Redevances en recul deux trimestres de suite ; augmentation de capital ; essai retardé ou décevant. Pas de renforcement |

Un mouvement de plus de 8 % dans la journée, ou une publication de résultats,
déclenche une analyse de la ligne par Claude le soir même.

## 8. Assurance vie

- **Boost du fonds euros** : prime d'intérêts versée fin janvier avec les
  intérêts du fonds euros. Deux conditions : chaque versement contient
  **au moins 30 % d'unités de compte**, et la part d'unités de compte du
  contrat **dépasse 30 % au 31 décembre**. Les deux sont toujours respectées,
  sauf décision contraire notée dans le journal (notes/).
- Poche unités de compte : **monétaire uniquement** (Amundi Euro Liquidity).
- Zone de pilotage : **32 à 35 %** d'unités de compte.
  - Au-dessus de 35 % : pas d'arbitrage ; les versements se font au minimum
    de 30 % d'unités de compte.
  - Sous 32 % : la part d'unités de compte des versements augmente (jusqu'à
    100 %) pour revenir dans la zone.
- **Revue du 5 février** : saisir dans apports.csv les intérêts du fonds euros
  et le boost crédités fin janvier (prix 0), puis recalculer la part d'unités
  de compte.
- **Revue du 5 décembre** : calculer la part d'unités de compte prévue au
  31 décembre, en supposant une baisse de 10 % des unités de compte actions.
  Sous 31 % : arbitrage du fonds euros vers Amundi Euro Liquidity avant le
  20 décembre.
- En décembre, la note quotidienne alerte si la part d'unités de compte passe
  sous 31 %.
- Arbitrage du 21/11/2026 de Carmignac Sécurité, de l'ETF Euro Corporate SRI et
  du reliquat ODDO 2029 vers Amundi Euro Liquidity : en cours ; les montants
  estimés de apports.csv seront remplacés par ceux de l'avis d'opéré.
- Le monétaire est la première réserve mobilisée par les paliers de forte baisse
  (avec la limite du §2).

## 9. Enveloppes

- **PEA en priorité** jusqu'au plafond de 150 000 € de versements ; alerte à 90 %.
- **PER** : pas de versement mensuel. Un versement en décembre seulement si le
  gain fiscal net est positif (taux marginal actuel 30 %).
- **Livrets** : intérêts à saisir au 31 décembre (prix 0), nouveau taux à
  ajouter dans supports.txt à chaque révision (1er février, 1er août).

## 10. Organisation

| Qui | Quand | Quoi |
|---|---|---|
| Workflow « Analyse historique » (telemesure-zone-euro) | Le 1er de chaque mois, 5 h | Mise à jour des fondamentaux des 263 valeurs suivies, utilisés pour juger les bonnes affaires |
| Script veille.py (GitHub Actions) | Chaque jour ouvré, 17 h 45 (18 h 45 l'été) | Mesures chiffrées, rapport dans rapports/derniere.md, alertes Telegram seulement s'il y a quelque chose |
| Claude (tâche planifiée) | Chaque jour ouvré, vers 20 h | Note quotidienne dans notes/, envoyée sur Telegram : marchés, signaux, verdict, lignes individuelles |
| Claude (tâche planifiée) | Le 5 de chaque mois, le matin | Revue mensuelle : répartition du versement, éventuel changement de cible |
| Daniel | À chaque décision | Exécution des ordres, saisie dans l'onglet Saisie |
