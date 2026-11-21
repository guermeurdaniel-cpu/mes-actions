# -*- coding: utf-8 -*-
"""Patch par remplacements (21/11/2026) : l indicateur « vs argent non place » est
exprime en % du patrimoine (capital affiche), et non plus des apports nets :
gain en euros = pourcentage x patrimoine. Applique par le workflow patch.yml ;
chaque texte doit etre trouve une seule fois, sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"index.html": [
("""    // Par rapport a l argent non place : patrimoine / apports nets cumules a la date - 1.
    // Les apports nets sont ce qui serait detenu si rien n avait ete place (ventes
    // deduites a leur prix, gains realises compris dans le resultat).
    const pctNp=totalSeries.values.map(function(v,i){ const c=investiA(td[i]); return c>0? (v/c-1)*100 : 0; });
    nonPlaceIdx=allCharts.length;
    allCharts.push({label:"Gain par rapport a l argent non place (% des apports nets)",""",
"""    // Par rapport a l argent non place : (patrimoine - apports nets cumules a la date)
    // / patrimoine de la date. Les apports nets sont ce qui serait detenu si rien n avait
    // ete place (ventes deduites a leur prix, gains realises compris dans le resultat).
    const pctNp=totalSeries.values.map(function(v,i){ const c=investiA(td[i]); return v>0? (v-c)/v*100 : 0; });
    nonPlaceIdx=allCharts.length;
    allCharts.push({label:"Gain par rapport a l argent non place (% du patrimoine)","""),
("""      const gNp=pmv.totDay-apportsNets, pNp=gNp/apportsNets*100;""",
"""      const gNp=pmv.totDay-apportsNets, pNp=(pmv.totDay>0? gNp/pmv.totDay*100 : 0);"""),
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
