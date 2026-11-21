# -*- coding: utf-8 -*-
"""Patch par remplacements (21/11/2026) : la courbe « Patrimoine total » en % suit
la meme definition que le chiffre du haut de la page. A chaque date : gains
cumules = somme, ligne par ligne, de (valeur - quantite detenue x prix de revient
a cette date) ; pourcentage = gains cumules / patrimoine a cette date. Applique
par le workflow patch.yml ; chaque texte doit etre trouve une seule fois, sinon
aucun fichier n est ecrit."""
import sys

PATCHS = {
"index.html": [
("""// Construit la serie temporelle du patrimoine consolide (somme qte*VL + fonds euros),
// limitee a la fenetre reellement enregistree (report de la derniere VL connue, jamais de reconstruction du passe).
function buildTotalSeries(data, hist, yres, costBasis){""",
"""// Cout de revient d une ligne a une date : quantite detenue x prix de revient
// (PRU) a cette date. null si aucun prix d achat connu.
function coutA(cle, date){
  const p=pruA(cle, date);
  return (p!=null)? qteA(cle, date)*p : null;
}
// Construit la serie temporelle du patrimoine consolide (somme qte*VL + fonds euros),
// limitee a la fenetre reellement enregistree (report de la derniere VL connue, jamais de reconstruction du passe).
// Renvoie aussi, a chaque date, le cout de revient des lignes detenues (costs) :
// gains cumules = values - costs, meme definition que la PMV du haut de la page.
function buildTotalSeries(data, hist, yres, costBasis){"""),
("""      if(y && y.q) series.push({ dates:y.q.dates, vals:y.q.closes.map(function(c,i){ return qteA(cle,y.q.dates[i])*c; }) });""",
"""      if(y && y.q) series.push({ cle:cle, dates:y.q.dates, vals:y.q.closes.map(function(c,i){ return qteA(cle,y.q.dates[i])*c; }) });"""),
("""      if(h.length) series.push({ dates:h.map(function(e){return e.date;}), vals:h.map(function(e){return qteA(cle,e.date)*e.value;}) });
      else if(f && f.value!=null) series.push({ dates:[todayStr()], vals:[q*f.value] });""",
"""      if(h.length) series.push({ cle:cle, dates:h.map(function(e){return e.date;}), vals:h.map(function(e){return qteA(cle,e.date)*e.value;}) });
      else if(f && f.value!=null) series.push({ cle:cle, dates:[todayStr()], vals:[q*f.value] });"""),
("""  const values=dates.map(function(){ return FONDS_EUROS; }); // fonds euros = constante a chaque date
  // Livrets : solde du journal + interets courus, a chaque date
  SUPPORTS.forEach(function(sup){
    if(!estFixe(sup.cle)) return;
    for(let i=0;i<dates.length;i++) values[i]+=valeurLivret(sup.cle, dates[i]);
  });""",
"""  const values=dates.map(function(){ return FONDS_EUROS; }); // fonds euros = constante a chaque date
  const costs=dates.map(function(){ return FONDS_EUROS_VERSE; });
  // Livrets et fonds euros : solde du journal + interets courus, a chaque date
  SUPPORTS.forEach(function(sup){
    if(!estFixe(sup.cle)) return;
    for(let i=0;i<dates.length;i++){
      const v=valeurLivret(sup.cle, dates[i]), c=coutA(sup.cle, dates[i]);
      values[i]+=v; costs[i]+=(c!=null? c : v);
    }
  });"""),
("""      if(m[dates[i]]!=null) last=m[dates[i]]; // sinon on reporte la derniere VL connue
      if(last!=null) values[i]+=last;""",
"""      if(m[dates[i]]!=null) last=m[dates[i]]; // sinon on reporte la derniere VL connue
      if(last!=null){
        values[i]+=last;
        const c=coutA(s.cle, dates[i]);
        costs[i]+=(c!=null? c : last);   // sans prix d achat connu : gain compte nul
      }"""),
("""    dates.unshift(REF_DATE);
    values.unshift(costBasis);
  }
  return { dates:dates, values:values };""",
"""    dates.unshift(REF_DATE);
    values.unshift(costBasis);
    costs.unshift(costBasis);
  }
  return { dates:dates, values:values, costs:costs };"""),
("""    // % rapporte au capital reellement investi A CETTE DATE : un apport fait en
    // cours de route ne se lit donc pas comme une performance
    const pct=totalSeries.values.map(function(v,i){ const c=investiA(td[i]); return c>0? (v/c-1)*100 : 0; });""",
"""    // A chaque date : gains cumules de toutes les lignes (valeur - cout de revient des
    // parts detenues) rapportes au patrimoine de cette date. Meme definition que le
    // chiffre du haut : le dernier point de la courbe lui correspond. Un apport ne se
    // lit pas comme une performance (il entre a son cout de revient).
    const pct=totalSeries.values.map(function(v,i){ const c=totalSeries.costs[i]; return v>0? (v-c)/v*100 : 0; });"""),
("""allCharts.push({label:"Patrimoine total (PMV en %)",""",
"""allCharts.push({label:"Patrimoine total (gains cumules en % du patrimoine)","""),
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
