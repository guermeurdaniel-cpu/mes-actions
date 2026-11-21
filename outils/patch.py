# -*- coding: utf-8 -*-
"""Patch ponctuel de index.html (21/11/2026) : cibles lues dans cibles.txt et
rapports/signaux.csv, libelles Monde hors Europe / Europe. Applique par le
workflow patch.yml ; chaque remplacement doit trouver son texte une seule fois,
sinon rien n est ecrit."""
import sys

F = "index.html"
s = open(F, encoding="utf-8").read()

REMPLACEMENTS = [
("""// --- Cibles d allocation ---
const TARGET_ACTIONS = 0.70;   // part actions visee sur le patrimoine consolide
const BANDE          = 0.05;   // demi-bande de reequilibrage, en points
const TARGET_EM      = 0.10;   // part emergents visee dans la poche actions
""",
"""// --- Cibles d allocation ---
// Valeurs de secours seulement : elles sont remplacees au chargement par
// cibles.txt (memes cibles que veille.py) et, si un palier de forte baisse est
// actif, par la cible du jour lue dans rapports/signaux.csv.
let TARGET_ACTIONS = 0.65;   // part actions visee sur le patrimoine consolide
let BANDE          = 0.05;   // demi-bande de reequilibrage, en points
let TARGET_EM      = 0.10;   // part emergents visee dans la poche actions
let TARGET_EUROPE  = 0.30;   // part Europe (toutes sources) visee dans la poche actions
let CIBLE_ORIGINE  = "valeurs par defaut";   // affiche sous la barre de repartition
"""),
("""async function chargerSupports(){""",
"""// Lit cibles.txt (nom = valeur) puis la derniere ligne de rapports/signaux.csv,
// qui donne la cible du jour (65 %, ou 70/75/80 % si un palier est actif).
async function chargerCibles(){
  try{
    const r=await fetch("cibles.txt?t="+Date.now(), {cache:"no-store"});
    if(r.ok){
      const c={};
      (await r.text()).split(/\\r?\\n/).forEach(function(brut){
        const l=brut.split("#")[0].trim(); const i=l.indexOf("=");
        if(i<0) return;
        const v=parseFloat(l.slice(i+1).trim().replace(",","."));
        if(!isNaN(v)) c[l.slice(0,i).trim()]=v;
      });
      if(c.actions!==undefined)   TARGET_ACTIONS=c.actions;
      if(c.bande!==undefined)     BANDE=c.bande;
      if(c.emergents!==undefined) TARGET_EM=c.emergents;
      if(c.europe!==undefined)    TARGET_EUROPE=c.europe;
      CIBLE_ORIGINE="cibles.txt";
    }
  }catch(e){}
  try{
    const r=await fetch("rapports/signaux.csv?t="+Date.now(), {cache:"no-store"});
    if(r.ok){
      const lignes=(await r.text()).trim().split(/\\r?\\n/);
      if(lignes.length>1){
        const tete=lignes[0].split(";"), der=lignes[lignes.length-1].split(";");
        const cible=parseFloat(der[tete.indexOf("cible")]);
        const palier=parseInt(der[tete.indexOf("palier")],10);
        if(palier>0 && !isNaN(cible)){
          TARGET_ACTIONS=cible;
          CIBLE_ORIGINE="palier "+palier+" de forte baisse (veille du "+der[tete.indexOf("date")]+")";
        }
      }
    }
  }catch(e){}
}

async function chargerSupports(){"""),
("""  const cat = await chargerSupports();""", """  await chargerCibles();
  const cat = await chargerSupports();"""),
("""    // Poche zone euro apportee par les fonds mixtes (actions x part euro de leur geo)
    var euroEqEquilibre=0;
    SUPPORTS.forEach(function(sup){
      if(sup.actions>0 && sup.actions<1) euroEqEquilibre += holdingEur(sup.cle)*sup.actions*sup.geo.euro;
    });
""", ""),
("""      '<div class="geo"><div class="meta">Repartition des actions (par indice) : '
      +'<span style="color:#5e9eff">Monde dev. '+gwP.toFixed(0)+'%</span> - '
      +'<span style="color:#ffd479">Zone euro '+geP.toFixed(0)+'%</span> - '
      +'<span style="color:#ff6482">Emergents '+gmP.toFixed(0)+'%</span></div>'
      +'<div class="barg"><div class="w" style="width:'+gwP.toFixed(1)+'%"></div><div class="e" style="width:'+geP.toFixed(1)+'%"></div><div class="m" style="width:'+gmP.toFixed(1)+'%"></div></div>'
      +'<div class="meta gap">Emergents : '+eur(gm)+' ('+gmP.toFixed(0)+'%).</div></div>';""",
"""      '<div class="geo"><div class="meta">Repartition geographique des actions : '
      +'<span style="color:#5e9eff">Monde hors Europe '+gwP.toFixed(0)+'%</span> - '
      +'<span style="color:#ffd479">Europe '+geP.toFixed(0)+'%</span> - '
      +'<span style="color:#ff6482">Emergents '+gmP.toFixed(0)+'%</span></div>'
      +'<div class="barg"><div class="w" style="width:'+gwP.toFixed(1)+'%"></div><div class="e" style="width:'+geP.toFixed(1)+'%"></div><div class="m" style="width:'+gmP.toFixed(1)+'%"></div></div>'
      +'<div class="meta gap">Europe (MSCI World compris) : '+eur(ge)+', cible '+(TARGET_EUROPE*100).toFixed(0)+'% - '
      +'Emergents : '+eur(gm)+', cible '+(TARGET_EM*100).toFixed(0)+'%.</div></div>';"""),
("""      +'<div class="meta" style="margin-top:6px">Dont actions zone euro (poche MSCI EMU de l Equilibre) : ~'+eur(euroEqEquilibre)+'</div>'
      +'<div class="meta" style="margin-top:4px">'+sig+'</div>'+geoHtml+'</div>';""",
"""      +'<div class="meta" style="margin-top:4px">'+sig+'</div>'
      +'<div class="meta" style="margin-top:2px;opacity:.7">Cible lue dans '+CIBLE_ORIGINE+'</div>'+geoHtml+'</div>';"""),
]

for ancien, nouveau in REMPLACEMENTS:
    n = s.count(ancien)
    if n != 1:
        print("ECHEC : texte trouve %d fois : %r" % (n, ancien[:80]))
        sys.exit(1)
    s = s.replace(ancien, nouveau)
open(F, "w", encoding="utf-8").write(s)
print("index.html : %d remplacements appliques" % len(REMPLACEMENTS))
