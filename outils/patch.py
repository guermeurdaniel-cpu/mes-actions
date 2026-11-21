# -*- coding: utf-8 -*-
"""Patch par remplacements (21/11/2026) : le fonds euros devient un support du
catalogue (source fixe, 1 part = 1 EUR), saisi dans apports.csv comme un livret,
au lieu d une valeur ecrite en dur dans index.html. Applique par le workflow
patch.yml ; chaque texte doit etre trouve une seule fois, sinon aucun fichier
n est ecrit."""
import sys

PATCHS = {
"supports.txt": [
("""# ================================== LIVRETS ==================================""",
"""[Fonds euros]
cle       = FONDS-EUROS
enveloppe = AV
source    = fixe
actions   = 0.00
# Fonds euros de l assurance vie BoursoVie. Gere comme un livret : 1 part = 1 EUR,
# versements saisis dans apports.csv (montant ; 1), participation aux benefices
# saisie au 31 decembre une fois creditee (montant ; 0). Pas de taux ici : le
# rendement n est connu qu en fin d annee. Ne compte pas dans les unites de compte.


# ================================== LIVRETS =================================="""),
],
"apports.csv": [
("""#  Le fonds euros de l assurance vie n est pas gere ici : il se saisit dans
#  index.html, constantes FONDS_EUROS (valeur du jour) et FONDS_EUROS_VERSE
#  (montant net verse).""",
"""#  FONDS EUROS (assurance vie) : gere comme un livret. Versement : montant ; 1.
#  Participation aux benefices, au 31 decembre une fois creditee : montant ; 0."""),
("""# --- Assurance vie -------------------------------------------------------
""",
"""# --- Assurance vie -------------------------------------------------------
2026-05-12;Fonds euros;6600;1
2026-05-20;Fonds euros;11335;1
# Ecart entre la valeur saisie jusqu ici (18 135) et les versements (17 935) :
# a confirmer ; si la valeur reelle est 17 935, supprimer la ligne suivante.
2026-06-16;Fonds euros;200;0
"""),
],
"index.html": [
("""const FONDS_EUROS       = 18135;   // valeur actuelle
const FONDS_EUROS_VERSE = 18135;   // montant net verse (le gain est la difference)""",
"""// Depuis le 21/11/2026 le fonds euros est un support du catalogue (source fixe,
// cle FONDS-EUROS) saisi dans apports.csv. Ces deux constantes restent a 0.
const FONDS_EUROS       = 0;
const FONDS_EUROS_VERSE = 0;"""),
("""  const totaux = { "PEG":0, "PEA":0, "AV":0, "LIV":0 };
""",
"""  const totaux = { "PEG":0, "PEA":0, "AV":0, "LIV":0 };
  let fondsEurosFixe=0;   // supports fixes de l assurance vie (fonds euros) : hors unites de compte
"""),
("""        totaux[env.name] += solde+inter;
        boite.appendChild(row);
        return;""",
"""        totaux[env.name] += solde+inter;
        if(env.name==="AV") fondsEurosFixe += solde+inter;
        boite.appendChild(row);
        return;"""),
("""  // Le fonds euros n est pas un support : il se saisit en montant, en fin d assurance vie
  const boiteAv=document.getElementById("av");
  if(boiteAv){
    const rowFE=document.createElement("div"); rowFE.className="row";
    rowFE.innerHTML='<div class="info"><div class="nm">Fonds euros</div><div class="sub"><span class="pr">'+eur(FONDS_EUROS)+'</span><span class="held">'+eur(FONDS_EUROS)+'</span></div></div><svg class="spark"></svg>';
    boiteAv.appendChild(rowFE);
  }

""", ""),
("""avUC=totaux["AV"];""", """avUC=totaux["AV"]-fondsEurosFixe;"""),
("""  const avTotal = avUC + FONDS_EUROS;""", """  const avTotal = avUC + fondsEurosFixe + FONDS_EUROS;"""),
("""      if(env.name==="AV"){                                   // fonds euros : gain = valeur - verse
        const feGain=FONDS_EUROS-FONDS_EUROS_VERSE;
        eGain+=feGain; lines.push({label:"Fonds euros", g:feGain});
      }
""", ""),
],
"veille.py": [
("""                           actions=s["actions"], geo=s["geo"], var_jour=var_jour,
                           individuelle=individuelle))""",
"""                           actions=s["actions"], geo=s["geo"], var_jour=var_jour,
                           individuelle=individuelle, fixe=(s["source"] == "fixe")))"""),
("""    av_uc = sum(l["valeur"] for l in lignes if l["env"] == "AV")
    uc_av = av_uc / (av_uc + fonds_euros) if (av_uc + fonds_euros) else 0""",
"""    av_uc = sum(l["valeur"] for l in lignes if l["env"] == "AV" and not l["fixe"])
    av_tot = sum(l["valeur"] for l in lignes if l["env"] == "AV") + fonds_euros
    uc_av = av_uc / av_tot if av_tot else 0"""),
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
