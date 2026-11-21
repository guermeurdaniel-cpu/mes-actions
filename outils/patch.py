# -*- coding: utf-8 -*-
"""Patch par remplacements (21/11/2026) : l en-tete lit realises.csv (plus et
moins-values des ventes, genere par realises.py) et affiche les gains et pertes
depuis juin 2026 : en cours (lignes detenues) + realises (ventes) = total, et son
% du patrimoine. Applique par le workflow patch.yml ; chaque texte doit etre
trouve une seule fois, sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"index.html": [
("""  try{
    const pR=await fetch("patrimoine.json?t="+Date.now());
    if(pR.ok){ const pj=await pR.json(); if(Array.isArray(pj)) patHist=pj; }
  }catch(e){}""",
"""  try{
    const pR=await fetch("patrimoine.json?t="+Date.now());
    if(pR.ok){ const pj=await pR.json(); if(Array.isArray(pj)) patHist=pj; }
  }catch(e){}
  // realises.csv : plus et moins-values des ventes, genere par realises.py a chaque
  // modification du journal. null si absent (calcul de secours plus bas).
  let realisesTot=null;
  try{
    const rR=await fetch("realises.csv?t="+Date.now(), {cache:"no-store"});
    if(rR.ok){
      let t=0;
      (await rR.text()).split(/\\r?\\n/).forEach(function(l){
        l=l.trim(); if(!l || l.charAt(0)==="#" || l.indexOf("date;")===0) return;
        const c=l.split(";"); const v=parseFloat(c[6]); if(!isNaN(v)) t+=v;
      });
      realisesTot=t;
    }
  }catch(e){}"""),
("""    // Gains ou pertes depuis juin 2026 : patrimoine - apports nets (versements moins
    // retraits, ventes comprises), rapportes au patrimoine du jour.
    const apportsNets=investiA(todayStr());
    if(apportsNets>0){
      const gJ=pmv.totDay-apportsNets, pJ=gJ/pmv.totDay*100, sgJ=gJ>=0?"+":"";
      progHtml+=
        '<div class="meta">Depuis juin 2026 : <span class="'+(gJ>=0?"prog-up":"prog-down")+'">'
        +sgJ+eur(gJ)+', soit '+sgJ+pJ.toFixed(2)+'% du patrimoine</span>'
        +' (ventes et arbitrages compris)</div>';
    }""",
"""    // Gains et pertes depuis juin 2026 : en cours (lignes detenues, PMV ci-dessus)
    // + realises (ventes, realises.csv) = total, rapporte au patrimoine du jour.
    // Secours si realises.csv manque : total = patrimoine - apports nets.
    const enCours=pmv.totGain;
    const realise=(realisesTot!==null)? realisesTot : (pmv.totDay-investiA(todayStr()))-enCours;
    const totJ=enCours+realise, pJ=totJ/pmv.totDay*100;
    function sgn(x){ return x>=0? "+" : ""; }
    function cls(x){ return x>=0? "prog-up" : "prog-down"; }
    progHtml+=
      '<div class="meta">Depuis juin 2026 : en cours <span class="'+cls(enCours)+'">'+sgn(enCours)+eur(enCours)+'</span>'
      +' + realises <span class="'+cls(realise)+'">'+sgn(realise)+eur(realise)+'</span>'
      +' = <span class="'+cls(totJ)+'">'+sgn(totJ)+eur(totJ)+', soit '+sgn(totJ)+pJ.toFixed(2)+'% du patrimoine</span></div>';"""),
],
}

nouveaux = {}
for fichier, remplacements in PATCHS.items():
    s = open(fichier, encoding="utf-8").read()
    for ancien, nouveau in remplacements:
        n = s.count(ancien)
        if n != 1:
            print("ECHEC %s : texte trouve %d fois : %r" % (fichier, n, ancien[:80]))
            sys.exit(1)
        s = s.replace(ancien, nouveau)
    nouveaux[fichier] = s
for fichier, s in nouveaux.items():
    open(fichier, "w", encoding="utf-8").write(s)
    print("%s : patch applique" % fichier)
