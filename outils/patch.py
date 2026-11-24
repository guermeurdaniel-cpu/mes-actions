# -*- coding: utf-8 -*-
"""Patch par remplacements (24/11/2026) : la courbe du patrimoine est recalculee
jour par jour depuis le 16/06/2026 (et non plus sur 3 mois avec un point
artificiel au 16/06). Les cours Yahoo sont charges sur un an ; les graphiques par
ligne restent sur 3 mois. Applique par le workflow patch.yml ; chaque texte doit
etre trouve une seule fois, sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"index.html": [
("""    const yurl = base + symbol + "?range=3mo&interval=1d";""",
"""    const yurl = base + symbol + "?range=1y&interval=1d";"""),
("""        return {price:price, prev:prev, prevDate:prevDate, prevSrc:prevSrc, cur:m.currency, closes:closes, dates:dates};""",
"""        // Un an de clotures pour la courbe du patrimoine (closesAll / datesAll) ; les
        // graphiques par ligne gardent les 3 derniers mois (closes / dates).
        const coupure=new Date(Date.now()-92*864e5).toISOString().slice(0,10);
        let k0=dates.findIndex(function(d){ return d>=coupure; }); if(k0<0) k0=0;
        return {price:price, prev:prev, prevDate:prevDate, prevSrc:prevSrc, cur:m.currency,
                closes:closes.slice(k0), dates:dates.slice(k0), closesAll:closes, datesAll:dates};"""),
("""      if(y && y.q) series.push({ cle:cle, dates:y.q.dates, vals:y.q.closes.slice() });""",
"""      if(y && y.q) series.push({ cle:cle, dates:(y.q.datesAll||y.q.dates).slice(), vals:(y.q.closesAll||y.q.closes).slice() });"""),
("""  // Fenetre honnete : on demarre a la date la plus tardive ou CHAQUE ligne a commence
  // a etre enregistree -> aucune valeur reconstruite vers le passe (pas de back-fill).
  let startDate=null;
  series.forEach(function(s){
    const fd=s.dates.slice().sort()[0];
    if(startDate===null || fd>startDate) startDate=fd;
  });""",
"""  // La courbe part du 16/06/2026 (REF_DATE, debut du journal) : chaque jour est
  // recalcule avec la quantite, le prix et le prix de revient de ce jour-la.
  const startDate=REF_DATE;"""),
("""    for(let i=0;i<sd.length;i++){ if(sd[i]<=startDate) last=m[sd[i]]; }""",
"""    for(let i=0;i<sd.length;i++){ if(sd[i]<=startDate) last=m[sd[i]]; }
    // Ligne dont le premier prix enregistre est posterieur au 16/06 (fonds du PEG
    // publies a partir du 18-19/06) : ce premier prix est reporte vers l arriere.
    if(last===null && sd.length) last=m[sd[0]];"""),
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
