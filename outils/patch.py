# -*- coding: utf-8 -*-
"""Patch par remplacements (24/11/2026) : dans la courbe du patrimoine, le report
de la derniere valeur connue reportait une VALEUR (quantite d une date passee x
prix). Une ligne vendue apres sa derniere VL publiee (Carmignac, ODDO, vendus le
21/11 avec une VL du 19/11 et du 17/11) restait donc comptee apres la vente, avec
un cout nul : gain fantome d environ 3 270 EUR, d ou l ecart entre la courbe et la
synthese. Desormais on reporte le PRIX, multiplie par la quantite detenue a
chaque date. Applique par le workflow patch.yml ; chaque texte doit etre trouve
une seule fois, sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"index.html": [
("""  const series=[]; // chaque element : {dates:[...], vals:[...]} en EUR""",
"""  const series=[]; // chaque element : {cle, dates:[...], vals:[...]} ; vals = prix unitaires (cloture ou VL)"""),
("""      if(y && y.q) series.push({ cle:cle, dates:y.q.dates, vals:y.q.closes.map(function(c,i){ return qteA(cle,y.q.dates[i])*c; }) });""",
"""      if(y && y.q) series.push({ cle:cle, dates:y.q.dates, vals:y.q.closes.slice() });"""),
("""      if(h.length) series.push({ cle:cle, dates:h.map(function(e){return e.date;}), vals:h.map(function(e){return qteA(cle,e.date)*e.value;}) });
      else if(f && f.value!=null) series.push({ cle:cle, dates:[todayStr()], vals:[q*f.value] });""",
"""      if(h.length) series.push({ cle:cle, dates:h.map(function(e){return e.date;}), vals:h.map(function(e){return e.value;}) });
      else if(f && f.value!=null) series.push({ cle:cle, dates:[todayStr()], vals:[f.value] });"""),
("""      if(m[dates[i]]!=null) last=m[dates[i]]; // sinon on reporte la derniere VL connue
      if(last!=null){
        values[i]+=last;
        const c=coutA(s.cle, dates[i]);
        costs[i]+=(c!=null? c : last);   // sans prix d achat connu : gain compte nul
      }""",
"""      if(m[dates[i]]!=null) last=m[dates[i]]; // sinon on reporte le dernier PRIX connu
      if(last!=null){
        // quantite detenue A CETTE DATE x dernier prix connu : une vente ou un achat
        // posterieur a la derniere VL publiee est bien pris en compte
        const v=qteA(s.cle, dates[i])*last;
        values[i]+=v;
        const c=coutA(s.cle, dates[i]);
        costs[i]+=(c!=null? c : v);   // sans prix d achat connu : gain compte nul
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
