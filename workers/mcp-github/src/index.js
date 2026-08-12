/**
 * Serveur MCP GitHub - Cloudflare Worker
 *
 * Expose trois outils a Claude : lire un fichier, ecrire un fichier, lister un
 * dossier, dans une liste fermee de depots GitHub.
 *
 * Le jeton GitHub ne quitte jamais ce Worker. Claude ne connait que l'URL, dont
 * un segment sert de mot de passe.
 *
 * Liaisons attendues (Settings du Worker) :
 *   GITHUB_TOKEN  secret - jeton fine-grained, permission Contents read+write
 *   CLE_MCP       secret - segment d'URL secret
 *
 * Point d'entree :  POST https://<worker>/<CLE_MCP>/mcp
 */

const PROPRIETAIRE = "guermeurdaniel-cpu";
const DEPOTS_AUTORISES = ["mes-actions", "telemesure-zone-euro", "peg-per",
                          "telemesure-boursiere", "paasi", "tgvmax-rennes"];
const BRANCHE_DEFAUT = "main";
const TAILLE_MAX = 400000;            // octets, garde-fou sur les ecritures
const VERSION_MCP = "2025-06-18";
const UA = "worker-mcp-github";

/* ---------- base64 compatible UTF-8 ---------- */

function b64encode(texte){
  const octets = new TextEncoder().encode(texte);
  let bin = "";
  for(let i=0;i<octets.length;i++) bin += String.fromCharCode(octets[i]);
  return btoa(bin);
}

function b64decode(b64){
  const bin = atob(String(b64).replace(/\s/g, ""));
  const octets = new Uint8Array(bin.length);
  for(let i=0;i<bin.length;i++) octets[i] = bin.charCodeAt(i);
  return new TextDecoder().decode(octets);
}

/* ---------- appels GitHub ---------- */

function verifierDepot(depot){
  if(DEPOTS_AUTORISES.indexOf(depot) < 0){
    throw new Error("Depot non autorise : " + depot
      + ". Depots ouverts : " + DEPOTS_AUTORISES.join(", "));
  }
}

async function github(env, methode, chemin, corps){
  const r = await fetch("https://api.github.com" + chemin, {
    method: methode,
    headers: {
      "Authorization": "Bearer " + env.GITHUB_TOKEN,
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": UA,
      "Content-Type": "application/json"
    },
    body: corps ? JSON.stringify(corps) : undefined
  });
  const texte = await r.text();
  let data = null;
  try{ data = texte ? JSON.parse(texte) : null; }catch(e){ data = { message: texte }; }
  if(!r.ok){
    const m = (data && data.message) ? data.message : ("HTTP " + r.status);
    throw new Error("GitHub " + r.status + " : " + m);
  }
  return data;
}

/* ---------- les trois outils ---------- */

async function lireFichier(env, a){
  verifierDepot(a.depot);
  const branche = a.branche || BRANCHE_DEFAUT;
  const d = await github(env, "GET",
    "/repos/" + PROPRIETAIRE + "/" + a.depot + "/contents/"
    + encodeURI(a.chemin) + "?ref=" + encodeURIComponent(branche));
  if(Array.isArray(d)) throw new Error(a.chemin + " est un dossier, pas un fichier");
  if(d.encoding !== "base64") throw new Error("Encodage inattendu : " + d.encoding);
  return "Fichier " + a.depot + "/" + a.chemin + " (branche " + branche
    + ", sha " + d.sha.slice(0,7) + ", " + d.size + " octets)\n\n" + b64decode(d.content);
}

async function ecrireFichier(env, a){
  verifierDepot(a.depot);
  if(!a.message) throw new Error("Le message de commit est obligatoire");
  const octets = new TextEncoder().encode(a.contenu).length;
  if(octets > TAILLE_MAX) throw new Error("Contenu trop volumineux : " + octets + " octets");
  const branche = a.branche || BRANCHE_DEFAUT;
  const url = "/repos/" + PROPRIETAIRE + "/" + a.depot + "/contents/" + encodeURI(a.chemin);

  // GitHub exige le sha de la version remplacee, pour refuser une ecriture
  // fondee sur un etat perime. Absent si le fichier n'existe pas encore.
  let sha = null;
  try{
    const actuel = await github(env, "GET", url + "?ref=" + encodeURIComponent(branche));
    if(!Array.isArray(actuel)) sha = actuel.sha;
  }catch(e){
    if(String(e.message).indexOf("404") < 0) throw e;
  }

  const corps = { message: a.message, content: b64encode(a.contenu), branch: branche };
  if(sha) corps.sha = sha;
  const d = await github(env, "PUT", url, corps);
  return (sha ? "Fichier mis a jour" : "Fichier cree") + " : "
    + a.depot + "/" + a.chemin + " (branche " + branche
    + ", commit " + d.commit.sha.slice(0,7) + ")";
}

async function listerDossier(env, a){
  verifierDepot(a.depot);
  const branche = a.branche || BRANCHE_DEFAUT;
  const chemin = a.chemin || "";
  const d = await github(env, "GET",
    "/repos/" + PROPRIETAIRE + "/" + a.depot + "/contents/"
    + encodeURI(chemin) + "?ref=" + encodeURIComponent(branche));
  if(!Array.isArray(d)) return chemin + " est un fichier (" + d.size + " octets)";
  const lignes = d.map(function(e){
    return (e.type === "dir" ? "[dossier] " : "          ") + e.name
         + (e.type === "file" ? ("  " + e.size + " o") : "");
  });
  return a.depot + "/" + (chemin || ".") + " (branche " + branche + ") : "
    + d.length + " entrees\n" + lignes.join("\n");
}

const OUTILS = [
  {
    name: "lire_fichier",
    description: "Lit le contenu d'un fichier texte dans un depot GitHub de Daniel.",
    inputSchema: {
      type: "object",
      properties: {
        depot:   { type: "string", enum: DEPOTS_AUTORISES, description: "Nom du depot" },
        chemin:  { type: "string", description: "Chemin du fichier depuis la racine, ex. index.html" },
        branche: { type: "string", description: "Branche, defaut " + BRANCHE_DEFAUT }
      },
      required: ["depot", "chemin"]
    }
  },
  {
    name: "ecrire_fichier",
    description: "Cree ou remplace un fichier et committe. Le contenu remplace "
      + "integralement l'ancien : envoyer le fichier complet, pas un extrait.",
    inputSchema: {
      type: "object",
      properties: {
        depot:   { type: "string", enum: DEPOTS_AUTORISES },
        chemin:  { type: "string", description: "Chemin du fichier depuis la racine" },
        contenu: { type: "string", description: "Contenu complet du fichier" },
        message: { type: "string", description: "Message de commit" },
        branche: { type: "string", description: "Branche, defaut " + BRANCHE_DEFAUT }
      },
      required: ["depot", "chemin", "contenu", "message"]
    }
  },
  {
    name: "lister_dossier",
    description: "Liste les fichiers et sous-dossiers d'un dossier du depot.",
    inputSchema: {
      type: "object",
      properties: {
        depot:   { type: "string", enum: DEPOTS_AUTORISES },
        chemin:  { type: "string", description: "Dossier, vide pour la racine" },
        branche: { type: "string", description: "Branche, defaut " + BRANCHE_DEFAUT }
      },
      required: ["depot"]
    }
  }
];

async function appelerOutil(env, nom, args){
  if(nom === "lire_fichier")   return await lireFichier(env, args || {});
  if(nom === "ecrire_fichier") return await ecrireFichier(env, args || {});
  if(nom === "lister_dossier") return await listerDossier(env, args || {});
  throw new Error("Outil inconnu : " + nom);
}

/* ---------- JSON-RPC / MCP ---------- */

function reponse(id, result){ return { jsonrpc: "2.0", id: id, result: result }; }
function erreur(id, code, message){
  return { jsonrpc: "2.0", id: id, error: { code: code, message: message } };
}

async function traiter(env, msg){
  const id = msg.id;
  switch(msg.method){
    case "initialize":
      return reponse(id, {
        protocolVersion: (msg.params && msg.params.protocolVersion) || VERSION_MCP,
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: "github-guermeurdaniel", version: "1.0.0" }
      });
    case "ping":
      return reponse(id, {});
    case "tools/list":
      return reponse(id, { tools: OUTILS });
    case "tools/call":
      try{
        const texte = await appelerOutil(env, msg.params.name, msg.params.arguments);
        return reponse(id, { content: [{ type: "text", text: texte }], isError: false });
      }catch(e){
        // Erreur applicative : renvoyee comme resultat, pour que Claude la lise.
        return reponse(id, { content: [{ type: "text", text: "Echec : " + e.message }], isError: true });
      }
    default:
      return erreur(id, -32601, "Methode inconnue : " + msg.method);
  }
}

export default {
  async fetch(request, env){
    const url = new URL(request.url);
    const segments = url.pathname.split("/").filter(Boolean);

    if(!env.CLE_MCP || segments[0] !== env.CLE_MCP || segments[1] !== "mcp"){
      return new Response("Not found", { status: 404 });
    }
    if(!env.GITHUB_TOKEN){
      return new Response("GITHUB_TOKEN absent", { status: 500 });
    }
    if(request.method !== "POST"){
      return new Response("Methode non autorisee", { status: 405 });
    }

    let corps;
    try{
      corps = await request.json();
    }catch(e){
      return Response.json(erreur(null, -32700, "JSON invalide"), { status: 400 });
    }

    // Les notifications n'ont pas d'identifiant et n'attendent pas de reponse.
    const lot = Array.isArray(corps) ? corps : [corps];
    const sorties = [];
    for(const msg of lot){
      if(msg && msg.id === undefined) continue;
      sorties.push(await traiter(env, msg));
    }
    if(!sorties.length) return new Response(null, { status: 202 });

    return Response.json(Array.isArray(corps) ? sorties : sorties[0]);
  }
};
