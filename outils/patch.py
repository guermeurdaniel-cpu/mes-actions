# -*- coding: utf-8 -*-
"""Patch par remplacements (21/11/2026) : suppression de la seconde courbe (« vs
argent non place ») ; a la place, une ligne dans l en-tete : gains ou pertes
depuis juin 2026 (patrimoine - apports nets, ventes comprises) et leur % du
patrimoine. Applique par le workflow patch.yml ; chaque texte doit etre trouve
une seule fois, sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"index.html": [
("""  let totalChartIdx=-1, realChartIdx=-1, nonPlaceIdx=-1, progHtml="";""",
"""  let totalChartIdx=-1, realChartIdx=-1, progHtml="";"""),
("""    // Par rapport a l argent non place : (patrimoine - apports nets cumules a la date)
    // / patrimoine de la date. Les apports nets sont ce qui serait detenu si rien n avait
    // ete place (ventes deduites a leur prix, gains realises compris dans le resultat).
    const pctNp=totalSeries.values.map(function(v,i){ const c=investiA(td[i]); return v>0? (v-c)/v*100 : 0; });
    nonPlaceIdx=allCharts.length;
    allCharts.push({label:"Gain par rapport a l argent non place (% du patrimoine)", dates:td, values:pctNp, up:(pctNp[pctNp.length-1]>=0), unit:"%"});
""", ""),
("""    // Second indicateur : resultat par rapport a l argent qui serait detenu sans aucun placement
    const apportsNets=investiA(todayStr());
    if(apportsNets>0){
      const gNp=pmv.totDay-apportsNets, pNp=(pmv.totDay>0? gNp/pmv.totDay*100 : 0);
      const clNp=gNp>=0?"prog-up":"prog-down", sgNp=gNp>=0?"+":"";
      const clicNp=(nonPlaceIdx>=0)?' onclick="openFullChart('+nonPlaceIdx+')"':'';
      progHtml+=
        '<br><div class="prog"'+clicNp+'>'
        +'<span class="pct '+clNp+'">'+sgNp+pNp.toFixed(2)+'%</span>'
        +'<span class="eurd '+clNp+'">'+sgNp+eur(gNp)+'</span>'
        +'<span class="since">vs argent non place ('+eur(apportsNets)+' apportes)</span>'
        +(nonPlaceIdx>=0?'<span class="tap">&#9654; courbe %</span>':'')+'</div>';
    }""",
"""    // Gains ou pertes depuis juin 2026 : patrimoine - apports nets (versements moins
    // retraits, ventes comprises), rapportes au patrimoine du jour.
    const apportsNets=investiA(todayStr());
    if(apportsNets>0){
      const gJ=pmv.totDay-apportsNets, pJ=gJ/pmv.totDay*100, sgJ=gJ>=0?"+":"";
      progHtml+=
        '<div class="meta">Depuis juin 2026 : <span class="'+(gJ>=0?"prog-up":"prog-down")+'">'
        +sgJ+eur(gJ)+', soit '+sgJ+pJ.toFixed(2)+'% du patrimoine</span>'
        +' (ventes et arbitrages compris)</div>';
    }"""),
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
