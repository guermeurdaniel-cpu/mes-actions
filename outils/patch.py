# -*- coding: utf-8 -*-
"""Patch par remplacements (28/11/2026) : frais de gestion trimestriels des unites
de compte de l assurance vie. index.html lit le nouveau champ frais de supports.txt
(% par trimestre) et deduit automatiquement, au dernier jour de chaque trimestre
echu, parts detenues x taux, sans prix (le PRU ne bouge pas, ce n est pas un
retrait). Les frais calcules n apparaissent pas dans les derniers mouvements de
l onglet Saisie. Meme calcul que supports.frais_trimestriels() cote Python.
Applique par le workflow patch.yml ; chaque texte doit etre trouve une seule fois,
sinon aucun fichier n est ecrit."""
import sys

PATCHS = {
"index.html": [
('actions:0, geo:{monde:0,euro:0,em:0}, taux:[], ligne:i+1};',
 'actions:0, geo:{monde:0,euro:0,em:0}, taux:[], frais:0, ligne:i+1};'),
('    else if(champ==="taux")      courant.taux=lireTaux(val, erreurs);\n',
 '    else if(champ==="taux")      courant.taux=lireTaux(val, erreurs);\n    else if(champ==="frais")     courant.frais=nombreFr(val)||0;\n'),
('  for(const cle in achats){ if(achats[cle].qte>0) PRU[cle]=achats[cle].cout/achats[cle].qte; }\n  APPORTS.sort(',
 '  for(const cle in achats){ if(achats[cle].qte>0) PRU[cle]=achats[cle].cout/achats[cle].qte; }\n  ajouterFrais();\n  APPORTS.sort('),
('async function chargerApports(){',
 '// Frais de gestion des unites de compte (champ frais de supports.txt, en % par\n// trimestre) : l assureur les preleve en diminuant le nombre de parts. On cree\n// un mouvement virtuel au dernier jour de chaque trimestre echu, egal aux parts\n// detenues ce jour-la x taux, sans prix : la quantite baisse, le PRU ne bouge\n// pas, et ce n est pas un retrait (investiA l ignore), donc c est une perte.\n// Meme calcul que supports.frais_trimestriels() cote Python.\nfunction ajouterFrais(){\n  const auj=todayStr();\n  SUPPORTS.forEach(function(s){\n    if(!s.frais) return;\n    const f=s.frais/100;\n    const mv=APPORTS.filter(function(a){ return a.cle===s.cle; });\n    const dates=mv.map(function(a){ return a.date; }).filter(Boolean).sort();\n    if(!dates.length) return;\n    const fins=["-03-31","-06-30","-09-30","-12-31"];\n    const prel=[];\n    for(let an=parseInt(dates[0].slice(0,4),10); an<=parseInt(auj.slice(0,4),10); an++){\n      for(let i=0;i<4;i++){\n        const d=an+fins[i];\n        if(d<dates[0] || d>auj) continue;\n        let det=0;\n        mv.forEach(function(a){ if(!a.date || a.date<=d) det+=a.qte; });\n        prel.forEach(function(x){ det+=x.qte; });\n        if(det>1e-6) prel.push({date:d, nom:s.nom, cle:s.cle, qte:-det*f, prix:null, frais:true});\n      }\n    }\n    prel.forEach(function(x){ APPORTS.push(x); QUANTITES[s.cle]=(QUANTITES[s.cle]||0)+x.qte; });\n    if(Math.abs(QUANTITES[s.cle]||0)<1e-6) QUANTITES[s.cle]=0;\n  });\n}\n\nasync function chargerApports(){'),
('  const n=APPORTS.length;\n  if(!n){',
 '  const reels=APPORTS.filter(function(a){ return !a.frais; });   // sans les frais calcules\n  const n=reels.length;\n  if(!n){'),
('  APPORTS.slice(Math.max(0,n-6)).reverse()',
 '  reels.slice(Math.max(0,n-6)).reverse()'),
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
