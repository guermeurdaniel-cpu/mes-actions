# Worker `mcp-github`

Serveur MCP qui permet a Claude de lire et d'ecrire directement dans les depots
GitHub de Daniel, depuis l'interface de conversation, y compris sur telephone.

Remplace le passage par Dropbox, juge trop lent : il fallait deposer un fichier,
demander la modification, recuperer le resultat, puis le recopier a la main dans
l'interface web de GitHub.

## Le principe : le concierge

Claude ne recoit jamais le jeton GitHub. Le Worker le detient, range dans le
coffre-fort de Cloudflare, et n'expose que trois actions. Claude lui passe
commande ; le Worker decide s'il execute.

Deux serrures independantes :

1. **Entre Claude et le Worker** — un segment d'URL secret (`CLE_MCP`). Toute
   autre valeur renvoie 404 sans appeler GitHub.
2. **Entre le Worker et GitHub** — un jeton fine-grained, permission Contents en
   lecture-ecriture uniquement. Meme si la premiere serrure cede, l'attaquant ne
   peut que modifier des fichiers, et chaque modification laisse une trace dans
   l'historique Git.

La liste `DEPOTS_AUTORISES`, en tete de `src/index.js`, restreint en dur les
depots accessibles.

## Fichiers

| Fichier | Role |
|---|---|
| `src/index.js` | Le code du Worker |
| `wrangler.jsonc` | Nom et parametres — la configuration du tableau de bord, sous forme de fichier |
| `README.md` | Ce document |

Ni cron, ni stockage KV : ce Worker ne fait que repondre a des requetes.

## Secrets a poser dans le tableau de bord

A poser en type **Secret** (jamais en type Text), dans Settings.

| Nom | Contenu |
|---|---|
| `GITHUB_TOKEN` | Jeton GitHub fine-grained, permission Contents read+write |
| `CLE_MCP` | Chaine aleatoire inventee, segment d'URL secret |

**`CLE_MCP` doit etre strictement alphanumerique.** Une premiere version
contenant `?`, `&`, `@` et `€` cassait le chemin de l'URL : le point
d'interrogation transformait la suite en chaine de parametres, le Worker ne
recevait qu'un fragment de la cle et renvoyait 404.

Le jeton GitHub a une date d'expiration. Le jour ou le connecteur cesse de
fonctionner sans raison apparente, c'est le premier suspect.

## Adresse a declarer dans Claude

```
https://mcp-github.guermeur-daniel.workers.dev/<CLE_MCP>/mcp
```

A coller dans Claude : Reglages > Connecteurs > Ajouter un connecteur
personnalise. A faire depuis un navigateur sur ordinateur ; une fois enregistre,
le connecteur est disponible partout, telephone compris.

## Les trois outils

| Outil | Effet |
|---|---|
| `lire_fichier` | Renvoie le contenu d'un fichier texte, avec son sha et sa taille |
| `ecrire_fichier` | Cree ou remplace un fichier et committe |
| `lister_dossier` | Liste les entrees d'un dossier, fichiers et sous-dossiers |

Tous acceptent un parametre `branche`, qui vaut `main` par defaut.

Pas d'outil de suppression : c'est delibere. Les suppressions se font a la main
dans l'interface GitHub.

## Points techniques

### Encodage

L'API GitHub transporte le contenu en base64. Les fonctions natives `btoa` et
`atob` travaillent octet par octet et cassent l'UTF-8, donc les accents. Le
Worker passe par `TextEncoder` et `TextDecoder` pour convertir proprement.
Verifie en production le 12/08/2026 : accents, ligatures et symbole euro
corrects.

### Ecriture concurrente

Avant de remplacer un fichier, le Worker lit sa version courante pour en
recuperer le `sha` et le transmettre. GitHub refuse ainsi une ecriture fondee sur
un etat perime. Le `sha` est omis lorsque le fichier n'existe pas encore.

### Garde-fou

Les ecritures sont plafonnees a 400 000 octets, pour eviter qu'une erreur
n'envoie un contenu aberrant.

### Protocole

JSON-RPC 2.0 sur HTTP POST, version MCP 2025-06-18. Methodes servies :
`initialize`, `ping`, `tools/list`, `tools/call`. Les notifications, sans
identifiant, recoivent un 202 sans corps. Les erreurs applicatives sont renvoyees
comme resultat avec `isError` a vrai, pour que Claude les lise et puisse
reagir, plutot que comme erreurs de protocole.

## Consommation

Quelques dizaines de requetes par jour au plus, a comparer aux 100 000 par jour
du plan gratuit Workers.
