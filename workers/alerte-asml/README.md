# Worker `alerte-asml`

Surveille **toutes les valeurs cotees declarees dans `supports.txt`** et envoie
un message Telegram quand la variation par rapport a la cloture de la seance
precedente franchit une bande de plus ou moins 3 %.

Le nom du Worker est reste `alerte-asml`, pour raison historique : il ne
surveillait au depart qu'ASML. Le renommer creerait un nouveau Worker et
obligerait a reposer les secrets, ce qui n'en vaut pas la peine.

Remplace le workflow GitHub Actions `.github/workflows/alerte-asml.yml`, qui
consommait environ 2 900 minutes d'execution par mois — un cout nul sur un depot
public, mais bien au-dela du quota gratuit de 2 000 minutes si le depot passe en
prive.

## Le catalogue fait foi

La liste des valeurs surveillees n'est **pas** dans ce code : elle est relue
dans `supports.txt` a chaque passage, soit toutes les cinq minutes.

- ajouter un bloc avec `source = yahoo` -> la valeur est surveillee au passage suivant
- retirer un bloc -> elle cesse de l'etre, et son etat est oublie
- changer l'intitule -> le nouveau nom apparait dans les messages

Aucun redeploiement n'est necessaire pour ces trois cas. Les fonds non cotes
(`amundi-ee`, `amundi-fr`, `abcbourse`, `boursier`) sont ignores : ils n'ont pas
de cours en direct, donc pas de variation du jour.

Un garde-fou plafonne la surveillance a 20 symboles par passage, pour rester
sous la limite de sous-requetes d'un Worker.

## Fichiers

| Fichier | Role |
|---|---|
| `src/index.js` | Le code du Worker |
| `wrangler.jsonc` | Nom, cron et liaison KV — la configuration du tableau de bord, sous forme de fichier |
| `README.md` | Ce document |

## Configuration a poser dans le tableau de bord

### Liaison KV

| Variable | Namespace |
|---|---|
| `ETAT` | `alerte-etat` |

Remplace le fichier `alerte_asml_state.json` de l'ancien workflow. **Une seule
cle**, nommee `etat`, contenant un objet indexe par symbole :

```
{"ASML.AS": {"date": "2026-08-12", "dansBande": true}, "AIR.PA": {...}}
```

L'objet est reconstruit a chaque passage a partir des seuls supports presents
dans le catalogue : c'est ce qui fait qu'une valeur retiree est oubliee sans
intervention. L'ancienne cle `asml`, heritee de la version mono-valeur, n'est
plus lue et peut etre supprimee.

Le nom de variable doit etre exactement `ETAT`.

### Secrets

A poser en type **Secret** (jamais en type Text), dans Settings.

| Nom | Contenu | Obligatoire |
|---|---|---|
| `TELEGRAM_TOKEN` | Jeton du bot Telegram | oui |
| `TELEGRAM_CHAT_ID` | Identifiant de la conversation destinataire | oui |
| `CLE_ACCES` | Chaine aleatoire inventee, protege les URL de diagnostic | oui |
| `GITHUB_TOKEN` | Jeton fine-grained, permission Contents en lecture | non |

`GITHUB_TOKEN` est facultatif tant que le depot est **public** : le catalogue est
alors lu par l'URL brute. Le jour ou le depot passe en prive, cette URL cesse de
repondre et il faut poser ce secret — le code bascule seul sur l'API GitHub, sans
autre modification.

### Declencheur

Cron Trigger : `*/5 8-18 * * 1-5` — heures UTC, comme sur GitHub Actions.

## Deploiement

**Automatique**, via Workers Builds : tout commit sur ce depot declenche une
construction et un deploiement. Le repertoire racine configure cote Cloudflare
est `workers/alerte-asml`.

Consequence : `wrangler.jsonc` fait foi pour le cron et la liaison KV. Une
modification faite dans le tableau de bord sera ecrasee au deploiement suivant.
Les secrets, eux, ne sont jamais touches par un deploiement.

## Points d'entree manuels

Proteges par le premier segment d'URL, qui doit valoir `CLE_ACCES`. Toute autre
valeur renvoie 404 sans appeler Yahoo ni ecrire quoi que ce soit.

- `/<CLE_ACCES>/etat` — diagnostic en JSON : pour chaque valeur du catalogue, le
  cours, la cloture de reference, sa date et sa provenance, plus l'etat stocke.
  **Ne declenche aucune alerte et n'ecrit rien.**
- `/<CLE_ACCES>/test` — execute la verification complete, ecrit dans le KV et
  envoie un message si une bande est franchie.

## Logique de calcul

### Le piege a eviter

`meta.chartPreviousClose` **ne designe pas la veille**. Ce champ vaut la cloture
de la seance precedant la fenetre demandee : avec `range=1mo`, c'est la cloture
d'il y a un mois. L'ancien workflow l'utilisait avec `range=2d` et comparait donc
le cours a J-2, affichant une variation cumulee sur deux seances.

`meta.previousClose` est absent des reponses observees.

### Le trou de la serie journaliere

Yahoo renvoie regulierement une seance avec `close = null` — constate sur ASML.AS
les 31/07/2026 et 04/08/2026. La ligne existe, seul le prix manque. Filtrer ces
lignes fait glisser la reference d'une seance.

Le code raisonne donc sur les tableaux bruts : le calendrier boursier de Yahoo
fait foi, la veille est la ligne d'avant celle de la seance en cours, que sa
valeur soit renseignee ou non.

### Le rattrapage

Quand la cloture de la veille est nulle, le Worker la reconstitue a partir de la
derniere bougie horaire non nulle de cette journee (`range=1mo&interval=60m`).

Fiabilite mesuree le 05/08/2026 : cloture officielle du 04/08 a 1472,60 EUR
contre 1472,80 obtenue par rattrapage, soit 0,20 EUR d'ecart (0,014 %).

Ces trous ne sont pas toujours definitifs : Yahoo avait comble celui du 04/08 en
fin de journee.

### Si aucune reference n'est trouvee

Pour la valeur concernee : aucune alerte, et son etat precedent est conserve tel
quel. Les autres valeurs continuent d'etre traitees normalement. Une bande a plus
ou moins 3 % calculee sur une reference inconnue vaudrait pire que rien.

Si c'est le **catalogue** qui est illisible, le passage entier est abandonne sans
rien ecrire.

## Anti-repetition

L'etat conserve, pour chaque valeur, si elle etait dans la bande au passage
precedent. Une alerte n'est envoyee qu'au moment du franchissement, pas a chaque
passage suivant. Le retour dans la bande rearme le mecanisme. Changement de jour
de bourse : remise a zero, on repart de « dans la bande ».

Quand plusieurs valeurs franchissent leur bande au meme passage — jour de forte
baisse, par exemple — elles sont regroupees dans **un seul message**, pour eviter
une rafale de notifications.

Le jour de bourse est derive de `gmtoffset`, pas de la date UTC du serveur.

## Consommation

Environ 130 passages par jour ouvre. Chaque passage fait une requete pour le
catalogue, puis une par valeur cotee — six aujourd'hui — plus une requete de
rattrapage par valeur trouee. Soit un ordre de grandeur de 1 000 requetes par
jour ouvre, a comparer aux 100 000 par jour du plan gratuit Workers.

L'ecriture KV n'a lieu que lorsque l'etat change, tres loin des 1 000 ecritures
quotidiennes autorisees.
