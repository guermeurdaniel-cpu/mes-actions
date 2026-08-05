# Worker `alerte-asml`

Surveille le cours d'ASML (ASML.AS, Euronext Amsterdam) et envoie un message
Telegram quand la variation par rapport a la cloture de la seance precedente
franchit une bande de plus ou moins 3 %.

Remplace le workflow GitHub Actions `.github/workflows/alerte-asml.yml`, qui
consommait environ 2 900 minutes d'execution par mois — un cout nul sur un depot
public, mais bien au-dela du quota gratuit de 2 000 minutes si le depot passe en
prive.

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

Remplace le fichier `alerte_asml_state.json` de l'ancien workflow. Une seule cle,
`asml`, contenant `{"date": "AAAA-MM-JJ", "dansBande": true|false}`.

Le nom de variable doit etre exactement `ETAT`.

### Secrets

A poser en type **Secret** (jamais en type Text), dans Settings.

| Nom | Contenu |
|---|---|
| `TELEGRAM_TOKEN` | Jeton du bot Telegram |
| `TELEGRAM_CHAT_ID` | Identifiant de la conversation destinataire |
| `CLE_ACCES` | Chaine aleatoire inventee, protege les URL de diagnostic |

Les valeurs ne sont volontairement pas reproduites ici. `TELEGRAM_TOKEN` et
`TELEGRAM_CHAT_ID` sont les memes que les secrets GitHub du meme nom.

### Declencheur

Cron Trigger : `*/5 8-18 * * 1-5` — heures UTC, comme sur GitHub Actions.

## Deploiement

Deploiement manuel, par le tableau de bord :

1. Workers & Pages > `alerte-asml` > Edit code
2. Coller le contenu de `src/index.js`, puis Deploy
3. Verifier dans Settings que la liaison, les secrets et le cron sont presents
4. Verifier que la version active est bien la derniere

Ajouter ou modifier une liaison ou un secret cree une nouvelle version : selon la
version du tableau de bord, elle est deployee automatiquement ou attend un clic
sur Deploy.

## Points d'entree manuels

Proteges par le premier segment d'URL, qui doit valoir `CLE_ACCES`. Toute autre
valeur renvoie 404 sans appeler Yahoo ni ecrire quoi que ce soit.

- `/<CLE_ACCES>/etat` — diagnostic en JSON : cours, cloture de reference, sa date
  et sa provenance, plus l'etat stocke. **Ne declenche aucune alerte et n'ecrit
  rien.**
- `/<CLE_ACCES>/test` — execute la verification complete, ecrit dans le KV et
  envoie un message Telegram si une borne est franchie.

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

Aucune alerte n'est emise et l'etat reste inchange. Une bande a plus ou moins 3 %
calculee sur une reference inconnue vaudrait pire que rien.

## Anti-repetition

L'etat conserve si le cours etait dans la bande au passage precedent. Une alerte
n'est envoyee qu'au moment du franchissement, pas a chaque passage suivant. Le
retour dans la bande rearme le mecanisme. Changement de jour de bourse : remise a
zero, on repart de « dans la bande ».

Le jour de bourse est derive de `gmtoffset`, pas de la date UTC du serveur.

## Consommation

Environ 130 executions par jour ouvre, soit 2 900 par mois — a comparer aux
100 000 requetes par jour du plan gratuit Workers. L'ecriture KV n'a lieu que
lorsque l'etat change, tres loin des 1 000 ecritures quotidiennes autorisees.
