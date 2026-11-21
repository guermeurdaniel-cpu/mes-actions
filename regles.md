# Règles de la stratégie de placement

Version du 21 novembre 2026. Document de référence commun au script quotidien
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
     compte actions, sans frais ni impôt ;
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

Répartition par défaut à partir du 5 décembre 2026 (validée le 21/11/2026) :

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
  validé, à partir de la part actions du versement.

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

- Poche unités de compte : **monétaire uniquement** (Amundi Euro Liquidity),
  entre **32 et 35 %** du contrat pour garder le bonus du fonds euros (seuil 30 %).
- Décision du 21/11/2026 : arbitrer Carmignac Sécurité, l'ETF Euro Corporate SRI
  et le reliquat ODDO 2029 vers Amundi Euro Liquidity (à faire après
  vérification de la règle exacte du bonus chez BoursoVie).
- Le monétaire est la première réserve mobilisée par les paliers de forte baisse.

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
