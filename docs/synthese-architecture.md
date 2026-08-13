# Synthese d'architecture — mes-actions

Mis a jour le 13 aout 2026.

Ce document sert de point de reprise : il doit suffire, seul, pour reprendre le
travail dans une nouvelle conversation sans rien reexpliquer. Il decrit ce qui
existe, pourquoi c'est fait ainsi, ce qui reste a faire, et les pieges deja
rencontres.

---

## 1. Vue d'ensemble

Trois briques, avec une ligne de partage nette.

| Brique | Role | Rythme |
|---|---|---|
| **GitHub** (depot `mes-actions`) | Source de verite : code, catalogue, journal des apports, historiques | Ecriture 3 fois/jour + saisies manuelles |
| **GitHub Actions** | Travail lourd : recuperation des valeurs liquidatives, calcul du patrimoine, telechargement des historiques | 3 passages/jour ouvre |
| **Cloudflare Workers** | Travail instantane : relais des cotations, alertes, ecriture GitHub pour Claude | A la demande / toutes les 5 min |

Principe directeur : **GitHub prepare, Cloudflare distribue.** Ce qui demande une
vraie machine (navigateur pilote, Python, bibliotheques compilees) reste sur
Actions. Ce qui doit arriver a l'instant ou quelqu'un regarde la page est fait
par un Worker.

Compte GitHub : `guermeurdaniel-cpu`, branche `main`, depots publics.
Compte Cloudflare : `7f43b9275a95d56b2c26a0f3f483b009`, sous-domaine
`guermeur-daniel.workers.dev`.

---

## 2. Structure du depot

```
index.html            tableau de bord (affichage pur)
supports.txt          catalogue : ce qui existe
apports.csv           journal date des mouvements : ce qui est detenu
supports.py           lecteur commun du catalogue
scraper.py            valeurs liquidatives (Amundi, abcbourse, boursier)
patrimoine.py         historisation du patrimoine total
cotations.py          telechargement des historiques CSV
nav.json              derniere VL de chaque fonds
history.json          serie des VL
patrimoine.json       serie du patrimoine total
*.csv                 historiques par valeur
.github/workflows/    update-nav.yml, cotations.yml
workers/alerte-asml/  code + doc du Worker d'alerte
workers/mcp-github/   code + doc du Worker connecteur MCP
docs/                 ce document
```

**Architecture a trois roles**, adoptee le 01/08/2026 : `supports.txt` decrit ce
qui existe, `apports.csv` decrit ce qui est detenu, `index.html` ne fait
qu'afficher. Ajouter une valeur se fait donc en un seul endroit, dans
`supports.txt`.

`apports.csv` doit rester classe par enveloppe, puis par support, puis par date.
Les en-tetes de commentaire `# --- PEG`, `# --- PEA`, `# --- Assurance vie`
servent de reperes au formulaire de saisie : ne pas les renommer.

---

## 3. Les trois Workers Cloudflare

### 3.1 `flat-bread-4d06` — relais Yahoo

Deploye le 22/07/2026. Contourne les proxies CORS publics, lents et peu fiables.
Interroge par `index.html` a chaque affichage. Format d'appel : le suffixe
`/?url=` fait partie de la valeur de `MON_PROXY` dans `mes-actions` (mais est
ajoute par le code dans `telemesure-zone-euro` — attention en cas de copie).

Piege corrige : le Worker renvoyait `Cache-Control: public, max-age=30`, repris
par le navigateur, donc le bouton Actualiser servait une reponse en cache.
Correctif : `fetch(target, {cache:"no-store"})`. Le meme risque existe toujours
dans `telemesure-zone-euro`.

### 3.2 `alerte-asml` — alertes de bande

Remplace l'ancien workflow GitHub Actions, qui consommait ~2 900 minutes/mois.
Nom conserve pour raison historique : le renommer creerait un nouveau Worker et
obligerait a reposer les secrets.

Surveille **toutes** les valeurs cotees de `supports.txt` — celles dont
`source = yahoo` — et envoie un message Telegram au franchissement d'une bande
de plus ou moins 3 %. La liste est relue a chaque passage : ajouter, retirer ou
renommer un support suffit, sans redeploiement.

- Cron : toutes les 5 min, 8h-18h UTC, du lundi au vendredi
- KV `ETAT`, namespace `alerte-etat`, **une seule cle** `etat` contenant un objet
  indexe par symbole, reconstruit a chaque passage (une valeur retiree est donc
  oubliee d'elle-meme)
- Secrets : `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, `CLE_ACCES`, et `GITHUB_TOKEN`
  facultatif
- Deploiement automatique par Workers Builds, repertoire racine
  `workers/alerte-asml`
- Diagnostic : `/<CLE_ACCES>/etat` (lecture seule) et `/<CLE_ACCES>/test`
  (execution complete)

`GITHUB_TOKEN` est inutile tant que le depot est public : le catalogue est lu par
l'URL brute. Le jour du passage en prive, poser ce secret suffit, le code bascule
seul sur l'API GitHub.

### 3.3 `mcp-github` — connecteur MCP

Permet a Claude de lire et d'ecrire dans les depots depuis l'interface de
conversation, telephone compris. Remplace le passage par Dropbox.

Trois outils : `lire_fichier`, `ecrire_fichier`, `lister_dossier`. Pas d'outil de
suppression, volontairement — les suppressions se font a la main.

Deux serrures : un segment d'URL secret (`CLE_MCP`) entre Claude et le Worker,
puis un jeton GitHub fine-grained entre le Worker et GitHub. La liste
`DEPOTS_AUTORISES`, en tete du code, restreint les depots accessibles aux six.

**Deploiement manuel, volontairement.** Ce Worker est l'outil qui permet de
committer : s'il etait deploye automatiquement, une version defectueuse
supprimerait le moyen de la corriger.

---

## 4. Le bug Yahoo — a ne pas reintroduire

Diagnostic du 05/08/2026, apres une variation d'ASML affichee a +3,38 % pour une
baisse reelle de 0,49 %.

**Cause.** La serie journaliere Yahoo (`interval=1d`) renvoie parfois une seance
avec `close = null` — constate les 31/07 et 04/08/2026. La ligne existe, seule la
valeur manque. Le code filtrait ces lignes, donc « l'avant-derniere bougie » ne
designait plus la veille mais l'avant-veille.

**Deux regles qui en decoulent.**

1. **Ne jamais utiliser `meta.chartPreviousClose`.** Ce champ designe la cloture
   precedant la fenetre demandee, pas la veille : avec `range=1mo` il valait
   1634,40, soit la cloture d'un mois plus tot. `meta.previousClose` est absent
   des reponses.
2. **Raisonner sur les tableaux bruts**, avant filtrage. Le calendrier boursier de
   Yahoo fait foi : la veille est la ligne d'avant celle de la seance en cours,
   que sa valeur soit renseignee ou non.

**Rattrapage.** Quand la cloture de la veille est nulle, elle est reconstituee a
partir de la derniere bougie horaire non nulle de cette journee
(`range=1mo&interval=60m`). Fiabilite mesuree : cloture officielle du 04/08 a
1472,60 EUR contre 1472,80 par rattrapage, soit 0,014 % d'ecart.

Ces trous ne sont pas toujours definitifs : Yahoo avait comble celui du 04/08 en
fin de journee.

**Correctif applique aux trois endroits** : `index.html`, le Worker d'alerte, et
`cotations.py`.

Autres corrections du meme jour :
- `index.html` : fenetre d'historique portee de 1 a 3 mois, trous combles sur
  toute la serie (donc le graphe aussi, pas seulement la variation du jour)
- `cotations.py` : fusionne desormais avec le CSV existant au lieu de l'ecraser
  (auparavant chaque execution pouvait detruire de l'historique), et date les
  seances avec `gmtoffset`
- `update-nav.yml` : passe de 11 a 3 passages par jour ouvre
  (`0 6,12,17 * * 1-5`), les VL ne changeant qu'une fois par jour

---

## 5. Workers Builds — et ses limites

Branche le 12/08/2026 sur `alerte-asml`. Un commit sur le depot declenche une
construction et un deploiement automatiques. Reglage critique : le **repertoire
racine**, `workers/alerte-asml`, sans barre oblique initiale.

Consequence : `wrangler.jsonc` fait foi pour le cron et la liaison KV. Une
modification faite dans le tableau de bord sera ecrasee au deploiement suivant.
Les secrets, eux, ne sont jamais touches.

**Limite genante, confirmee le 13/08/2026 :** Workers Builds ne respecte pas le
marqueur `[skip ci]` (supporte par Cloudflare Pages seulement) et n'a pas de
champ « Build watch paths ». **Tout** commit reconstruit, y compris les ecritures
de donnees faites par les workflows. C'est cosmetique — quelques constructions
inutiles par jour — mais ca encombre l'historique des versions.

Deux remedes possibles, aucun mis en oeuvre :
- separer le code des Workers dans un depot distinct (le plus propre, et compatible
  avec le projet de portefeuilles multiples)
- deployer par GitHub Actions avec `wrangler-action` et un filtre `paths`

Point en suspens : wrangler avertit que les Preview URLs sont activees par defaut
(route `workers.dev` active, `preview_urls` absent de `wrangler.jsonc`).

---

## 6. Ce qui reste a faire

- **Regenerer les CSV** avec le nouveau `cotations.py` : lancer le workflow
  « Telecharge cotation » une fois par symbole, et lire les lignes de rapport en
  fin d'execution (seances nulles rencontrees, reconstituees, toujours absentes)
- **Deconnecter Dropbox**, cote Claude puis dans les applications connectees du
  compte Dropbox
- **Supprimer l'ancienne cle KV `asml`**, orpheline depuis le passage a la cle
  unique `etat`
- Figer la version de wrangler dans un `package.json` (actuellement 4.122.0
  telechargee a la volee a chaque construction)

Mesure faite le 05/08/2026 sur les trous des CSV : 24 jours ouvres absents sur
5 ans pour les valeurs Euronext (~4,8/an), 43 a 49 pour les ETF americains et
londoniens (~9,8/an). Les jours feries boursiers en representent l'essentiel : les
vrais trous se comptent sur les doigts d'une main. Les backtests ASML ne sont pas
a refaire.

---

## 7. Projet en cours de conception — portefeuilles multiples

**Objectif.** Passer `mes-actions` en prive. Faire servir la page par Cloudflare
au lieu de GitHub Pages. Gerer plusieurs portefeuilles distincts : celui de
Daniel, et celui de sa mere dont l'adresse serait transmise a ses freres et
soeurs pour qu'ils suivent l'evolution, avec une cle d'acces a renseigner. Les
fichiers de gestion doivent etre distincts.

**Rien n'est construit a ce jour.**

### Ce que le passage en prive casse

- GitHub Pages ne publie plus rien
- les URL brutes de GitHub ne repondent plus
- le quota d'Actions passe d'illimite a 2 000 minutes/mois

Les deux premiers points sont remplaces par un Worker. Le troisieme est deja
anticipe : la sortie de l'alerte et la reduction des passages des VL ramenent la
consommation autour de 300 minutes/mois pour un portefeuille.

### Decoupage envisage

```
portefeuilles/
  daniel/    supports.txt  apports.csv  nav.json  history.json  patrimoine.json
  maman/     supports.txt  apports.csv  nav.json  history.json  patrimoine.json
commun/      index.html  supports.py  scraper.py  patrimoine.py  cotations.py
```

Code commun, donnees separees. Les scripts prennent le nom du portefeuille en
parametre ; les workflows tournent une fois par portefeuille.

### Role du Worker de presentation

Quatre roles, aucun tenable ailleurs :

1. **servir la page** — lire `index.html` dans le depot prive avec son jeton
2. **servir les donnees** — le navigateur ne peut pas lire un depot prive
3. **garder la porte** — seul endroit ou verifier la cle et decider qui voit quoi
4. **relayer les cotations** — role deja tenu par `flat-bread-4d06`, qu'on
   pourrait fusionner dans le meme Worker

Lecture par l'API GitHub a la demande, avec un cache court (~60 s), plutot qu'un
hebergement de fichiers statiques : rien n'est expose publiquement, et le depot
reste l'unique source de verite.

### Controle d'acces

Deux voies :

- **Cle par portefeuille** (`CLE_DANIEL`, `CLE_MAMAN`), saisie une fois puis
  memorisee par un cookie signe. Simple, maitrise dans le code. Inconvenient :
  cle partagee, revocation collective.
- **Cloudflare Access** (gratuit jusqu'a 50 utilisateurs), code a usage unique
  par adresse mail, revocation individuelle. Plus rigoureux, mais configuration
  dans la partie Zero Trust du tableau de bord.

Recommandation : commencer par la cle, garder Access en reserve.

Nuance pratique : 40 caracteres aleatoires conviennent a un secret qu'on colle
une fois, pas a une cle qu'un humain tape sur un telephone. Prevoir plutot une
quinzaine de caracteres, ou une phrase dictable.

### Question d'isolement — a trancher avant de construire

Un jeton GitHub fine-grained s'attribue **par depot, pas par dossier**. Deux
portefeuilles dans le meme depot ne sont donc pas cloisonnes : tout jeton qui lit
l'un peut lire l'autre. La separation en sous-dossiers organise, elle ne protege
pas.

| Montage | Isolement | Cout |
|---|---|---|
| 1 Worker, 1 depot | logique (dans le code) | minimal |
| 2 Workers, 1 depot | aucun gain reel | double configuration |
| 2 Workers, 2 depots | structurel | double configuration + code duplique ou parametre |

Avis retenu : **un seul Worker**, a condition que la partie qui decide qui voit
quoi tienne en une quinzaine de lignes relisibles — table figee associant chaque
cle a un portefeuille, aucun chemin construit a partir de ce que le visiteur
envoie. Si cette partie devient touffue en l'ecrivant, basculer sur deux Workers
et deux depots. Le risque encouru est l'embarras, pas le prejudice : personne ne
peut passer d'ordre avec ces donnees.

### Ordre de migration propose

1. Reorganiser les dossiers avec le seul portefeuille de Daniel, et faire servir
   la page par le Worker **pendant que le depot est encore public** — filet de
   securite
2. Passer en prive, poser les jetons
3. Ajouter le portefeuille de la mere
4. Ajouter l'authentification en dernier, quand le reste est stable

### La vraie inconnue

**Que contient le portefeuille de la mere, et ou trouver les cours ?** Si ses
supports ne sont ni sur Yahoo ni chez Amundi, il faudra ecrire de nouveaux
recuperateurs. C'est la que se situe l'essentiel du travail reel, pas dans
l'architecture.

Autre point a decider : le Worker d'alerte doit-il surveiller les deux
portefeuilles, ou seulement celui de Daniel ?

---

## 8. Pieges rencontres — a ne pas refaire

- **Cle secrete d'URL** : strictement alphanumerique. Une premiere cle contenant
  `?`, `&`, `@` et `€` cassait le chemin — le point d'interrogation transformait
  la suite en chaine de parametres, d'ou un 404 incomprehensible.
- **Expression cron dans un commentaire de bloc JavaScript** : une etoile suivie
  d'une barre oblique ferme le commentaire et casse le fichier. L'ecrire en
  toutes lettres.
- **Valider avec `node --check` meme les commits qui ne touchent que des
  commentaires.** C'est precisement celui-la qui a casse une construction.
- **Repertoire racine de Workers Builds** : sans barre oblique initiale,
  `workers/alerte-asml` et non `/workers/alerte-asml`.
- **Les secrets ne sont pas partages entre Workers.** Chacun a son propre
  coffre-fort ; un jeton pose sur `mcp-github` est invisible depuis
  `alerte-asml`.
- **Encodage base64** : `btoa` et `atob` travaillent octet par octet et cassent
  l'UTF-8. Passer par `TextEncoder` et `TextDecoder`.
- **Ecriture GitHub** : lire d'abord le fichier pour recuperer son `sha` et le
  transmettre, sinon GitHub refuse (ou pire, accepte une ecriture fondee sur un
  etat perime). Le `sha` est omis si le fichier n'existe pas.
- **Le tableau de bord Cloudflare s'affiche mal** sur le PC sous Windows 8 : le
  libelle des boutons devient invisible alors que le lien reste actif. Utiliser
  Firefox.
- **Ne pas faire ecrire l'etat d'un Worker dans GitHub** : chaque ecriture
  declencherait une reconstruction et un redeploiement du Worker lui-meme. C'est
  a ca que sert le KV.

---

## 9. Repartition GitHub / Cloudflare / KV

| Donnee | Ou | Pourquoi |
|---|---|---|
| Code, catalogue, journal des apports | GitHub | durable, merite un historique date et reversible |
| VL, patrimoine, historiques CSV | GitHub | produit par Actions, consulte par la page |
| Etat des bandes d'alerte | KV | volatile, sans interet historique, ecrit plusieurs fois par jour |
| Cotations en direct | nulle part | relayees a la demande par un Worker |
| Secrets et jetons | Coffre-fort Cloudflare, par Worker | jamais dans le depot, jamais relisibles |
