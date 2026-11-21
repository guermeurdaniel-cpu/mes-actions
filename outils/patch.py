# -*- coding: utf-8 -*-
"""Patch par remplacements (21/11/2026) : nouvel indicateur « gain par rapport a
l argent non place » = patrimoine - apports nets (ce qui serait detenu si rien
n avait ete place), en euros et en % des apports nets, avec sa courbe. Applique
par le workflow patch.yml ; chaque texte doit etre trouve une seule fois, sinon
aucun fichier n est ecrit."""
import sys

PATCHS = {
"index.html": [
("""  let totalChartIdx=-1, realChartIdx=-1, progHtml="";""",
"""  let totalChartIdx=-1, realChartIdx=-1, nonPlaceIdx=-1, progHtml="";"""),
("""allCharts.push({label:"Patrimoine total (gains cumules en % du patrimoine)", dates:td, values:pct, up:(pct[pct.length-1]>=0), unit:"%", isTotal:true, compareValues:totalSeries.values});""",
"""allCharts.push({label:"Patrimoine total (gains cumules en % du patrimoine)", dates:td, values:pct, up:(pct[pct.length-1]>=0), unit:"%", isTotal:true, compareValues:totalSeries.values});
    // Par rapport a l argent non place : patrimoine / apports nets cumules a la date - 1.
    // Les apports nets sont ce qui serait detenu si rien n avait ete place (ventes
    // deduites a leur prix, gains realises compris dans le resultat).
    const pctNp=totalSeries.values.map(function(v,i){ const c=investiA(td[i]); return c>0? (v/c-1)*100 : 0; });
    nonPlaceIdx=allCharts.length;
    allCharts.push({label:"Gain par rapport a l argent non place (% des apports nets)", dates:td, values:pctNp, up:(pctNp[pctNp.length-1]>=0), unit:"%"});"""),
("""      +(realChartIdx>=0?'<span class="tap" onclick="event.stopPropagation();openFullChart('+realChartIdx+')">&#9654; patrimoine EUR</span>':'')+'</div>';
  }
""",
"""      +(realChartIdx>=0?'<span class="tap" onclick="event.stopPropagation();openFullChart('+realChartIdx+')">&#9654; patrimoine EUR</span>':'')+'</div>';
    // Second indicateur : resultat par rapport a l argent qui serait detenu sans aucun placement
    const apportsNets=investiA(todayStr());
    if(apportsNets>0){
      const gNp=pmv.totDay-apportsNets, pNp=gNp/apportsNets*100;
      const clNp=gNp>=0?"prog-up":"prog-down", sgNp=gNp>=0?"+":"";
      const clicNp=(nonPlaceIdx>=0)?' onclick="openFullChart('+nonPlaceIdx+')"':'';
      progHtml+=
        '<br><div class="prog"'+clicNp+'>'
        +'<span class="pct '+clNp+'">'+sgNp+pNp.toFixed(2)+'%</span>'
        +'<span class="eurd '+clNp+'">'+sgNp+eur(gNp)+'</span>'
        +'<span class="since">vs argent non place ('+eur(apportsNets)+' apportes)</span>'
        +(nonPlaceIdx>=0?'<span class="tap">&#9654; courbe %</span>':'')+'</div>';
    }
  }
"""),
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
