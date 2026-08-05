/**
 * Alerte ASML - Cloudflare Worker
 * Remplace le workflow GitHub Actions .github/workflows/alerte-asml.yml
 *
 * Liaisons attendues (onglet Settings du Worker) :
 *   ETAT              KV namespace  - remplace alerte_asml_state.json
 *   TELEGRAM_TOKEN    secret
 *   TELEGRAM_CHAT_ID  secret
 *   CLE_ACCES         secret        - segment d'URL pour les appels manuels
 *
 * Declencheur Cron :  0/5 8-18 * * 1-5   (heures UTC)
 */

const SYMBOLE    = "ASML.AS";
const BORNE_BAS  = -3.0;   // % sous la cloture de la seance precedente
const BORNE_HAUT =  3.0;   // % au-dessus
const CLE_ETAT   = "asml";
const CHART      = "https://query1.finance.yahoo.com/v8/finance/chart/";

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
async function evaluer(){
  const res = await chartJson(SYMBOLE, "?range=1mo&interval=1d");
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
      veille = await clotureIntraday(SYMBOLE, jourVeille);
      source = (veille != null) ? "rattrapage horaire" : "introuvable";
    }
  }

  if(cours == null || !veille){
    return { ok:false, refJour:refJour, jourVeille:jourVeille, source:source };
  }
  return {
    ok: true, cours: cours, veille: veille, jourVeille: jourVeille,
    source: source, refJour: refJour,
    variation: (cours - veille) / veille * 100
  };
}

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
  let r;
  try{
    r = await evaluer();
  }catch(err){
    return "Yahoo injoignable : " + err.message;
  }

  if(!r.ok){
    // Sans reference fiable, une bande a +/-3% ne veut rien dire :
    // on n'alerte pas et on laisse l'etat inchange.
    return "Reference de veille indisponible (seance " + r.jourVeille + ") - aucune alerte";
  }

  const dansBande = (r.variation >= BORNE_BAS && r.variation <= BORNE_HAUT);

  const stocke = await env.ETAT.get(CLE_ETAT);
  let etat = null;
  if(stocke){ try{ etat = JSON.parse(stocke); }catch(err){ etat = null; } }
  // Nouveau jour de bourse -> on repart de "dans la bande".
  const etaitDansBande = (etat && etat.date === r.refJour) ? etat.dansBande : true;
  const franchissement = etaitDansBande && !dansBande;

  const nouveau = JSON.stringify({ date: r.refJour, dansBande: dansBande });
  if(nouveau !== stocke) await env.ETAT.put(CLE_ETAT, nouveau);

  const entete = SYMBOLE + "  cours=" + r.cours.toFixed(2)
    + "  veille=" + r.veille.toFixed(2) + " (" + r.jourVeille + ", " + r.source + ")"
    + "  variation=" + (r.variation>=0?"+":"") + r.variation.toFixed(2) + "%";

  if(!franchissement){
    return entete + "  -> " + (dansBande ? "dans la bande" : "hors bande, deja signale");
  }

  const sens  = (r.variation < BORNE_BAS) ? "BASSE" : "HAUTE";
  const rond  = (r.variation < 0) ? "\u{1F534}" : "\u{1F7E2}";
  const heure = new Date().toISOString().slice(11,16) + " UTC";
  const msg =
    rond + " ALERTE ASML - Franchissement borne " + sens + "\n" +
    "Cours : " + r.cours.toFixed(2) + " EUR\n" +
    "Variation : " + (r.variation>=0?"+":"") + r.variation.toFixed(2) +
      "% (veille " + r.jourVeille + " : " + r.veille.toFixed(2) + " EUR)\n" +
    "Bande : [" + BORNE_BAS + "%, " + BORNE_HAUT + "%]\n" +
    "Heure : " + heure;

  const envoi = await envoyerTelegram(env, msg);
  return entete + "  -> FRANCHISSEMENT " + sens + " (" + envoi + ")";
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
      const r = await evaluer().catch(function(e){ return { erreur: e.message }; });
      const stocke = await env.ETAT.get(CLE_ETAT);
      return Response.json({ evaluation: r, etatStocke: stocke });
    }
    if(chemin[1] === "test"){
      return new Response(await verifier(env), { headers:{ "Content-Type":"text/plain; charset=utf-8" } });
    }
    return new Response("Not found", { status: 404 });
  }
};
