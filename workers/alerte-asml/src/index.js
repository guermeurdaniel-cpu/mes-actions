/**
 * Alertes de bande - Cloudflare Worker
 * Remplace le workflow GitHub Actions .github/workflows/alerte-asml.yml
 *
 * Surveille TOUTES les valeurs cotees declarees dans supports.txt, a la racine
 * du depot mes-actions, et envoie un message Telegram quand la variation par
 * rapport a la cloture de la seance precedente franchit la bande.
 *
 * La liste n'est PAS figee dans ce fichier : elle est relue a chaque passage.
 * Ajouter, retirer ou renommer un support dans supports.txt suffit, sans
 * redeploiement. Une valeur retiree cesse d'etre surveillee et son etat est
 * oublie au passage suivant.
 *
 * Deploiement : automatique via Workers Builds, depuis ce depot.
 * Le fichier wrangler.jsonc fait foi pour le cron et la liaison KV : une
 * modification faite dans le tableau de bord Cloudflare sera ecrasee au
 * deploiement suivant.
 *
 * Liaisons attendues (onglet Settings du Worker) :
 *   ETAT              KV namespace  - remplace alerte_asml_state.json
 *   TELEGRAM_TOKEN    secret
 *   TELEGRAM_CHAT_ID  secret
 *   CLE_ACCES         secret        - segment d'URL pour les appels manuels
 *   GITHUB_TOKEN      secret        - FACULTATIF, voir chargerSupports()
 *
 * Declencheur Cron : toutes les 5 minutes, de 8h a 18h UTC, du lundi au
 * vendredi. L'expression exacte est declaree dans wrangler.jsonc (ne pas
 * l'ecrire ici : une etoile suivie d'une barre oblique fermerait ce
 * commentaire et casserait le fichier).
 */

const PROPRIETAIRE = "guermeurdaniel-cpu";
const DEPOT        = "mes-actions";
const BRANCHE      = "main";
const FICHIER      = "supports.txt";

const BORNE_BAS  = -3.0;   // % sous la cloture de la seance precedente
const BORNE_HAUT =  3.0;   // % au-dessus
const MAX_SYMBOLES = 20;   // garde-fou : plafond de sous-requetes par passage
const CLE_ETAT   = "etat"; // une seule cle KV, un objet indexe par symbole
const CHART      = "https://query1.finance.yahoo.com/v8/finance/chart/";

/* ---------- catalogue des supports ---------- */

/**
 * Decoupe supports.txt en blocs [Intitule] suivis de lignes "nom = valeur",
 * et ne garde que les supports dont la source est yahoo : les fonds non cotes
 * n'ont pas de cours en direct, donc pas de variation du jour.
 */
function analyserSupports(texte){
  const supports = [];
  let courant = null;
  for(const brute of texte.split("\n")){
    const ligne = brute.trim();
    if(!ligne || ligne.charAt(0) === "#") continue;
    if(ligne.charAt(0) === "[" && ligne.indexOf("]") > 0){
      if(courant) supports.push(courant);
      courant = { titre: ligne.slice(1, ligne.indexOf("]")).trim() };
      continue;
    }
    const eq = ligne.indexOf("=");
    if(courant && eq > 0){
      courant[ligne.slice(0, eq).trim().toLowerCase()] = ligne.slice(eq + 1).trim();
    }
  }
  if(courant) supports.push(courant);
  return supports.filter(function(s){
    return s.cle && (s.source || "").toLowerCase() === "yahoo";
  });
}

/**
 * Lit supports.txt dans le depot.
 * Avec GITHUB_TOKEN : par l'API Contents, ce qui continuera de fonctionner si
 * le depot passe en prive. Sans jeton : par l'URL brute, qui exige un depot
 * public. Les deux voies sont equivalentes tant que le depot est public.
 */
async function chargerSupports(env){
  if(env.GITHUB_TOKEN){
    const r = await fetch("https://api.github.com/repos/" + PROPRIETAIRE + "/" + DEPOT
      + "/contents/" + FICHIER + "?ref=" + BRANCHE, {
      headers: {
        "Authorization": "Bearer " + env.GITHUB_TOKEN,
        "Accept": "application/vnd.github.raw",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "worker-alertes"
      }
    });
    if(!r.ok) throw new Error("GitHub HTTP " + r.status + " sur " + FICHIER);
    return analyserSupports(await r.text());
  }
  const r = await fetch("https://raw.githubusercontent.com/" + PROPRIETAIRE + "/" + DEPOT
    + "/" + BRANCHE + "/" + FICHIER, { cf: { cacheTtl: 0 } });
  if(!r.ok) throw new Error("raw.githubusercontent HTTP " + r.status + " sur " + FICHIER);
  return analyserSupports(await r.text());
}

/* ---------- cotations ---------- */

function jourDe(sec, off){
  // Horodatages Yahoo en UTC : on ajoute le decalage de la place avant de dater.
  return new Date((sec + off) * 1000).toISOString().slice(0, 10);
}

async function chartJson(symbole, params){
  const r = await fetch(CHART + encodeURIComponent(symbole) + params, {
    headers: { "User-Agent": "Mozilla/5.0", "Accept": "application/json" },
    cf: { cacheTtl: 0, cacheEverything: false }
  });
  if(!r.ok) throw new Error("Yahoo HTTP " + r.status);
  const d = await r.json();
  const res = d && d.chart && d.chart.result && d.chart.result[0];
  if(!res) throw new Error("Reponse Yahoo inattendue");
  return res;
}

function extraire(res){
  const meta   = res.meta;
  const off    = meta.gmtoffset || 0;
  const ts     = res.timestamp || [];
  const closes = (res.indicators && res.indicators.quote && res.indicators.quote[0].close) || [];
  return { meta: meta, off: off, ts: ts, closes: closes };
}

// Derniere bougie horaire non nulle d'une journee donnee.
// Sert quand la serie journaliere renvoie la seance avec close = null.
async function clotureIntraday(symbole, jour){
  try{
    const res = await chartJson(symbole, "?range=1mo&interval=60m");
    const e = extraire(res);
    let val = null;
    for(let i=0;i<e.closes.length;i++){
      if(e.closes[i]!=null && jourDe(e.ts[i], e.off) === jour) val = e.closes[i];
    }
    return val;
  }catch(err){
    return null;
  }
}

/**
 * Cours du moment et cloture de la seance precedente.
 * range=1mo pour disposer du calendrier boursier complet : Yahoo renvoie la
 * ligne de chaque seance meme quand la cloture manque (close = null).
 * meta.chartPreviousClose n'est PAS utilise : ce champ designe la seance
 * precedant la fenetre demandee, pas la veille.
 */
async function evaluer(symbole){
  const res = await chartJson(symbole, "?range=1mo&interval=1d");
  const e = extraire(res);
  const cours = e.meta.regularMarketPrice;
  const jours = e.ts.map(function(t){ return jourDe(t, e.off); });
  const refJour = jourDe(e.meta.regularMarketTime != null
                          ? e.meta.regularMarketTime
                          : Math.floor(Date.now()/1000), e.off);

  let idxCourant = -1;
  for(let i=jours.length-1;i>=0;i--){ if(jours[i] === refJour){ idxCourant = i; break; } }
  // Bougie du jour presente -> la veille est juste avant.
  // Bougie du jour absente  -> la veille est la derniere ligne.
  const idxVeille = (idxCourant > 0) ? idxCourant - 1
                  : (idxCourant < 0 ? jours.length - 1 : -1);

  let veille = null, jourVeille = null, source = "";
  if(idxVeille >= 0){
    jourVeille = jours[idxVeille];
    if(e.closes[idxVeille] != null){
      veille = e.closes[idxVeille];
      source = "serie journaliere";
    }else{
      veille = await clotureIntraday(symbole, jourVeille);
      source = (veille != null) ? "rattrapage horaire" : "introuvable";
    }
  }

  if(cours == null || !veille){
    return { symbole:symbole, ok:false, refJour:refJour, jourVeille:jourVeille, source:source };
  }
  return {
    symbole: symbole, ok: true, cours: cours, veille: veille,
    jourVeille: jourVeille, source: source, refJour: refJour,
    devise: e.meta.currency || "",
    variation: (cours - veille) / veille * 100
  };
}

/* ---------- alerte ---------- */

async function envoyerTelegram(env, texte){
  if(!env.TELEGRAM_TOKEN || !env.TELEGRAM_CHAT_ID) return "secrets Telegram absents";
  try{
    const r = await fetch("https://api.telegram.org/bot" + env.TELEGRAM_TOKEN + "/sendMessage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: env.TELEGRAM_CHAT_ID, text: texte })
    });
    const d = await r.json();
    return d.ok ? "message envoye" : ("Telegram erreur : " + JSON.stringify(d));
  }catch(err){
    return "Telegram indisponible : " + err.message;
  }
}

async function verifier(env){
  let supports;
  try{
    supports = await chargerSupports(env);
  }catch(err){
    // Sans catalogue, on ne sait pas quoi surveiller : on ne touche a rien.
    return "Catalogue illisible : " + err.message + " - aucune alerte";
  }
  if(!supports.length) return "Aucun support cote dans " + FICHIER + " - aucune alerte";
  if(supports.length > MAX_SYMBOLES){
    supports = supports.slice(0, MAX_SYMBOLES);
  }

  const stocke = await env.ETAT.get(CLE_ETAT);
  let ancien = {};
  if(stocke){ try{ ancien = JSON.parse(stocke) || {}; }catch(err){ ancien = {}; } }

  const nouveau = {};          // reconstruit a partir des seuls supports courants
  const lignes = [];           // journal
  const franchissements = [];  // a signaler

  for(const s of supports){
    let r;
    try{
      r = await evaluer(s.cle);
    }catch(err){
      lignes.push(s.cle + " : Yahoo injoignable (" + err.message + ")");
      if(ancien[s.cle]) nouveau[s.cle] = ancien[s.cle];  // etat conserve tel quel
      continue;
    }
    if(!r.ok){
      lignes.push(s.cle + " : reference de veille indisponible (seance " + r.jourVeille + ")");
      if(ancien[s.cle]) nouveau[s.cle] = ancien[s.cle];
      continue;
    }

    const dansBande = (r.variation >= BORNE_BAS && r.variation <= BORNE_HAUT);
    const av = ancien[s.cle];
    // Nouveau jour de bourse, ou support jamais vu -> on repart de "dans la bande".
    const etaitDansBande = (av && av.date === r.refJour) ? av.dansBande : true;
    nouveau[s.cle] = { date: r.refJour, dansBande: dansBande };

    lignes.push(s.cle + " " + r.cours.toFixed(2)
      + "  veille " + r.veille.toFixed(2) + " (" + r.jourVeille + ", " + r.source + ")"
      + "  " + (r.variation>=0?"+":"") + r.variation.toFixed(2) + "%"
      + "  -> " + (dansBande ? "dans la bande"
                             : (etaitDansBande ? "FRANCHISSEMENT" : "hors bande, deja signale")));

    if(etaitDansBande && !dansBande) franchissements.push({ support: s, r: r });
  }

  const texteEtat = JSON.stringify(nouveau);
  if(texteEtat !== stocke) await env.ETAT.put(CLE_ETAT, texteEtat);

  let envoi = "";
  if(franchissements.length){
    const heure = new Date().toISOString().slice(11,16) + " UTC";
    const corps = franchissements.map(function(f){
      const sens = (f.r.variation < BORNE_BAS) ? "borne BASSE" : "borne HAUTE";
      const rond = (f.r.variation < 0) ? "\u{1F534}" : "\u{1F7E2}";
      return rond + " " + f.support.titre + " (" + f.r.symbole + ") - " + sens + "\n"
        + "Cours : " + f.r.cours.toFixed(2) + " " + f.r.devise + "\n"
        + "Variation : " + (f.r.variation>=0?"+":"") + f.r.variation.toFixed(2)
        + "% (veille " + f.r.jourVeille + " : " + f.r.veille.toFixed(2) + ")";
    }).join("\n\n");
    const entete = (franchissements.length === 1)
      ? "ALERTE - Franchissement de bande\n\n"
      : "ALERTE - " + franchissements.length + " franchissements de bande\n\n";
    envoi = await envoyerTelegram(env,
      entete + corps + "\n\nBande : [" + BORNE_BAS + "%, " + BORNE_HAUT + "%]\nHeure : " + heure);
  }

  const oublies = Object.keys(ancien).filter(function(k){ return !(k in nouveau); });
  return supports.length + " support(s) surveille(s)"
    + (oublies.length ? "  |  retires du catalogue : " + oublies.join(", ") : "")
    + (franchissements.length ? "  |  " + franchissements.length + " franchissement(s) (" + envoi + ")" : "")
    + "\n" + lignes.join("\n");
}

export default {
  // Declenchement automatique par le Cron Trigger
  async scheduled(event, env, ctx){
    ctx.waitUntil(verifier(env).then(function(m){ console.log(m); }));
  },

  // Appels manuels, proteges par un segment d'URL secret :
  //   /<CLE_ACCES>/etat  -> diagnostic seul, aucune alerte, aucune ecriture
  //   /<CLE_ACCES>/test  -> execute la verification complete
  async fetch(request, env, ctx){
    const chemin = new URL(request.url).pathname.split("/").filter(Boolean);
    if(!env.CLE_ACCES || chemin[0] !== env.CLE_ACCES){
      return new Response("Not found", { status: 404 });
    }
    if(chemin[1] === "etat"){
      let supports = [], erreur = null;
      try{ supports = await chargerSupports(env); }catch(e){ erreur = e.message; }
      const evaluations = [];
      for(const s of supports){
        const r = await evaluer(s.cle).catch(function(e){
          return { symbole: s.cle, erreur: e.message };
        });
        r.titre = s.titre;
        evaluations.push(r);
      }
      return Response.json({
        catalogue: erreur ? ("ERREUR : " + erreur) : (supports.length + " support(s) cote(s)"),
        bande: [BORNE_BAS, BORNE_HAUT],
        evaluations: evaluations,
        etatStocke: await env.ETAT.get(CLE_ETAT)
      });
    }
    if(chemin[1] === "test"){
      return new Response(await verifier(env), { headers:{ "Content-Type":"text/plain; charset=utf-8" } });
    }
    return new Response("Not found", { status: 404 });
  }
};
