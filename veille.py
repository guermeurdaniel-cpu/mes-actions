# -*- coding: utf-8 -*-
"""
veille.py — Controle quotidien de la strategie (regles.md, cibles.txt).

Lance chaque jour ouvre apres la cloture par .github/workflows/veille.yml.
Aucune IA ici : uniquement des mesures et des comparaisons a des seuils ecrits.

Ce que le script mesure :
  1. la repartition actions / defensif du patrimoine consolide (livrets compris)
     et son ecart a la cible ;
  2. la baisse du MSCI World (WPEA.PA) depuis son plus haut sur un an, et le
     palier de forte baisse correspondant ;
  3. la part d emergents dans la poche actions, la part d unites de compte de
     l assurance vie, le cumul des versements PEA ;
  4. les lignes individuelles : poids, mouvement du jour ;
  5. la liste des « bonnes affaires » candidates (univers de telemesure-zone-euro) ;
  6. les signaux de fond : inflation zone euro, tendance des matieres premieres,
     ecart emergents / monde, euro-dollar ;
  7. le rappel du versement mensuel.

Ce qu il ecrit :
  rapports/derniere.md              le rapport du jour (lu par Claude chaque soir)
  rapports/veille-AAAA-MM-JJ.md     archive
  rapports/signaux.csv              historique des signaux (une ligne par jour)
  rapports/candidats.json           candidats du jour, pour reperer les nouveaux

Telegram : un message seulement s il y a au moins une alerte.
Chaque bloc est protege : une source indisponible est signalee dans le rapport
sans arreter le reste.
"""

import csv
import datetime
import json
import os
import re
import urllib.request

from curl_cffi import requests as creq

import supports as supports_mod
import patrimoine as pat

AUJ = datetime.date.today()
JOUR = AUJ.isoformat()
DOSSIER = "rapports"
URL_ZE = "https://raw.githubusercontent.com/guermeurdaniel-cpu/telemesure-zone-euro/main/"
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range={rng}&interval=1d"
URL_INFLATION = ("https://data-api.ecb.europa.eu/service/data/ICP/M.U2.N.000000.4.ANR"
                 "?lastNObservations=1&format=jsondata")
URL_INFLATION_EUROSTAT = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
                          "prc_hicp_manr?format=JSON&geo=EA&coicop=CP00&lastTimePeriod=1")
SYM_MONDE, SYM_EM, SYM_MP, SYM_CHANGE = "WPEA.PA", "PAASI.PA", "EXXY.DE", "EURUSD=X"
PERSISTANCE = 20   # jours de bourse pour qu un signal de fond soit "confirme"


# ----------------------------------------------------------------------------
#  Lecture des cibles
# ----------------------------------------------------------------------------
def lire_cibles(chemin="cibles.txt"):
    c = {}
    with open(chemin, encoding="utf-8") as f:
        for brut in f:
            ligne = brut.split("#", 1)[0].strip()
            if "=" not in ligne:
                continue
            k, v = (x.strip() for x in ligne.split("=", 1))
            c[k] = float(v.replace(",", "."))
    return c


# ----------------------------------------------------------------------------
#  Sources de donnees
# ----------------------------------------------------------------------------
def serie_yahoo(sym, rng="1y"):
    """[(date, cloture), ...] tries, ou [] si echec."""
    try:
        r = creq.get(CHART.format(sym=sym, rng=rng), impersonate="chrome", timeout=25)
        res = r.json()["chart"]["result"][0]
        off = res["meta"].get("gmtoffset", 0) or 0
        ts = res.get("timestamp") or []
        cl = res["indicators"]["quote"][0]["close"]
        pts = []
        for t, v in zip(ts, cl):
            if v is not None:
                pts.append((datetime.datetime.utcfromtimestamp(t + off).date(), float(v)))
        return pts
    except Exception as e:
        print("  Yahoo KO %s : %s" % (sym, e))
        return []


def lire_json_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "mes-actions-veille"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def inflation_zone_euro():
    """(valeur en %, mois) de l IPCH zone euro en glissement annuel, ou (None, None).
    Deux sources (Eurostat, BCE) : on garde le mois le plus recent. Une donnee de
    plus de 3 mois est jugee perimee et ecartee."""
    trouves = []
    try:
        d = lire_json_url(URL_INFLATION_EUROSTAT)
        idx = d["dimension"]["time"]["category"]["index"]
        mois = max(idx, key=lambda k: idx[k])
        v = d["value"].get(str(idx[mois]))
        if v is not None:
            trouves.append((mois, float(v), "Eurostat"))
    except Exception as e:
        print("  Inflation Eurostat KO : %s" % e)
    try:
        d = lire_json_url(URL_INFLATION)
        serie = list(d["dataSets"][0]["series"].values())[0]["observations"]
        cle = sorted(serie.keys(), key=int)[-1]
        mois = d["structure"]["dimensions"]["observation"][0]["values"][int(cle)]["id"]
        trouves.append((mois, float(serie[cle][0]), "BCE"))
    except Exception as e:
        print("  Inflation BCE KO : %s" % e)
    if not trouves:
        return None, None
    mois, v, src = max(trouves)
    a, m = int(mois[:4]), int(mois[5:7])
    if (AUJ.year - a) * 12 + AUJ.month - m > 3:
        print("  Inflation perimee (%s, %s)" % (mois, src))
        return None, "%s, perime" % mois
    return v, "%s, %s" % (mois, src)


def perf(pts, jours_bourse):
    """Performance sur les n dernieres seances (ou depuis le debut si moins)."""
    if len(pts) < 2:
        return None
    i = max(0, len(pts) - 1 - jours_bourse)
    return pts[-1][1] / pts[i][1] - 1


# ----------------------------------------------------------------------------
#  Portefeuille
# ----------------------------------------------------------------------------
def valoriser(series):
    """Valeur du jour de chaque support : liste de dict, plus le fonds euros."""
    intit = supports_mod.par_intitule(pat.SUPPORTS)
    quant = pat.lire_apports(intit)
    mvts = pat.lire_mouvements(intit)
    with open("nav.json", encoding="utf-8") as f:
        nav = json.load(f)
    lignes, manquants = [], []
    for s in pat.SUPPORTS:
        cle, q = s["cle"], quant.get(s["cle"], 0.0)
        if not q:
            continue
        v, var_jour = None, None
        if s["source"] == "fixe":
            v = supports_mod.valeur_livret(s["taux"], mvts.get(cle, []), JOUR)
        elif s["source"] == "yahoo":
            pts = series.get(cle) or serie_yahoo(cle, "1mo")
            series[cle] = pts
            if pts:
                v = q * pts[-1][1]
                if len(pts) >= 2:
                    var_jour = pts[-1][1] / pts[-2][1] - 1
            elif nav.get(cle, {}).get("value") is not None:
                v = q * float(nav[cle]["value"])
        else:
            if nav.get(cle, {}).get("value") is not None:
                v = q * float(nav[cle]["value"])
        if v is None:
            manquants.append(s["nom"])
            continue
        individuelle = (s["source"] == "yahoo" and s["actions"] >= 1.0
                        and not s["nom"].upper().startswith("ETF"))
        lignes.append(dict(nom=s["nom"], cle=cle, env=s["enveloppe"], valeur=v,
                           actions=s["actions"], geo=s["geo"], var_jour=var_jour,
                           individuelle=individuelle))
    return lignes, pat.lire_fonds_euros(), manquants, mvts


def cumul_versements_pea():
    """Somme des achats moins ventes au prix du journal, enveloppe PEA. Approximatif :
    les lignes d ancrage du 16/06/2026 sont des valorisations, pas des versements."""
    env = dict((s["nom"], s["enveloppe"]) for s in pat.SUPPORTS)
    total = 0.0
    with open("apports.csv", encoding="utf-8-sig") as f:
        for brut in f:
            l = brut.strip()
            if not l or l.startswith("#"):
                continue
            c = l.split(";")
            if len(c) < 4 or env.get(c[1].strip()) != "PEA":
                continue
            q, p = pat.nombre_fr(c[2]), pat.nombre_fr(c[3])
            if q is not None and p is not None:
                total += q * p
    return total


# ----------------------------------------------------------------------------
#  Bonnes affaires
# ----------------------------------------------------------------------------
def candidats(cib):
    """Valeurs saines en forte baisse, a partir de telemesure-zone-euro."""
    data = lire_json_url(URL_ZE + "data.json")
    fiches = lire_json_url(URL_ZE + "analyse/fondamentaux.json").get("fiches", {})
    out, sans_fiche = [], 0
    for a in data.get("series", []):
        if not a.get("mk") or a.get("src") != "yahoo":
            continue
        pts = [(datetime.datetime.utcfromtimestamp(x / 1000).date(), y)
               for x, y in zip(a["x"], a["y"]) if y is not None]
        if len(pts) < 20:
            continue
        i_max = max(range(len(pts)), key=lambda i: pts[i][1])
        baisse = 1 - pts[-1][1] / pts[i_max][1]
        if baisse < cib["ba_baisse_min"]:
            continue
        f = fiches.get(a["tk"])
        if not f:
            sans_fiche += 1
            continue
        if (f.get("sector") or "") == "Financial Services":
            continue
        ebitda = f.get("ebitda") or 0
        dette_nette = (f.get("totalDebt") or 0) - (f.get("totalCash") or 0)
        lev = dette_nette / ebitda if ebitda > 0 else None
        fcf, marge, roe = f.get("freeCashflow"), f.get("operatingMargins"), f.get("returnOnEquity")
        sain = (lev is not None and lev < cib["ba_dette_ebitda_max"]
                and fcf is not None and fcf > 0
                and marge is not None and marge > cib["ba_marge_op_min"]
                and roe is not None and roe > cib["ba_rentabilite_min"])
        if not sain:
            continue
        # Choc = derniere seance ou le titre a perdu 10 % ou plus sur 5 seances ;
        # a defaut, la date du plus haut. Le delai d un mois court depuis ce choc.
        choc = pts[i_max][0]
        for i in range(max(i_max, 5), len(pts)):
            if pts[i][1] / pts[i - 5][1] - 1 <= -0.10:
                choc = pts[i][0]
        jours = (pts[-1][0] - choc).days
        out.append(dict(tk=a["tk"], nom=a["name"], baisse=baisse, jours=jours, choc=choc.isoformat(),
                        delai_ok=jours >= cib["ba_delai_jours"],
                        lev=lev, marge=marge, roe=roe, pf=a.get("pf")))
    out.sort(key=lambda c: -c["baisse"])
    return out, sans_fiche


# ----------------------------------------------------------------------------
#  Historique des signaux
# ----------------------------------------------------------------------------
CHAMPS = ["date", "part_actions", "cible", "palier", "baisse_monde", "part_em",
          "uc_av", "sig_mp", "sig_em", "inflation", "nb_candidats"]


def lire_historique():
    chemin = os.path.join(DOSSIER, "signaux.csv")
    if not os.path.exists(chemin):
        return []
    with open(chemin, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f, delimiter=";") if r.get("date") != JOUR]


def ecrire_historique(hist, ligne):
    chemin = os.path.join(DOSSIER, "signaux.csv")
    hist = hist + [ligne]
    with open(chemin, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CHAMPS, delimiter=";")
        w.writeheader()
        for r in hist:
            w.writerow(dict((k, r.get(k, "")) for k in CHAMPS))


def jours_consecutifs(hist, champ, valeur_du_jour):
    """Nombre de seances consecutives (aujourd hui compris) ou le signal vaut la meme
    chose, non nulle."""
    if not valeur_du_jour or valeur_du_jour == "0":
        return 0
    n = 1
    for r in reversed(hist):
        if r.get(champ) == str(valeur_du_jour):
            n += 1
        else:
            break
    return n


# ----------------------------------------------------------------------------
#  Utilitaires d affichage
# ----------------------------------------------------------------------------
def pc(x, signe=False):
    if x is None:
        return "n.d."
    s = ("%+.1f %%" if signe else "%.1f %%") % (100 * x)
    return s.replace(".", ",")


def pts_txt(x):
    return "n.d." if x is None else ("%+.1f points" % (100 * x)).replace(".", ",")


def levier_txt(lev):
    return "tresorerie nette" if lev < 0 else ("dette/EBITDA %.1f" % lev).replace(".", ",")


def eur(x):
    return ("{:,.0f} EUR".format(x)).replace(",", " ")


def est_jour_versement(cib):
    """Le 5 du mois, ou le premier jour ouvre suivant si le 5 tombe un week-end."""
    j = int(cib["jour_versement"])
    d = AUJ.replace(day=j)
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    return AUJ == d


def telegram(texte):
    tok, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not tok or not chat:
        print("  Telegram : secrets absents, message non envoye")
        return
    for i in range(0, len(texte), 3800):
        morceau = texte[i:i + 3800]
        try:
            r = creq.post("https://api.telegram.org/bot%s/sendMessage" % tok,
                          data={"chat_id": chat, "text": morceau}, timeout=20)
            print("  Telegram : HTTP %s" % r.status_code)
        except Exception as e:
            print("  Telegram KO : %s" % e)


# ----------------------------------------------------------------------------
#  Programme principal
# ----------------------------------------------------------------------------
def main():
    cib = lire_cibles()
    os.makedirs(DOSSIER, exist_ok=True)
    hist = lire_historique()
    veille = hist[-1] if hist else {}
    alertes, sections, ko = [], [], []

    # --- Series de reference
    series = {}
    for sym in (SYM_MONDE, SYM_EM, SYM_MP, SYM_CHANGE):
        series[sym] = serie_yahoo(sym, "1y")

    # --- 1. Repartition
    lignes, fonds_euros, manquants, _ = valoriser(series)
    if manquants:
        ko.append("supports sans valeur : " + ", ".join(manquants))
    total = sum(l["valeur"] for l in lignes) + fonds_euros
    actions = sum(l["valeur"] * l["actions"] for l in lignes)
    part_act = actions / total if total else 0

    # --- 2. Forte baisse
    monde = series[SYM_MONDE]
    baisse_monde, palier = None, 0
    if monde:
        haut = max(v for _, v in monde)
        baisse_monde = 1 - monde[-1][1] / haut
        for k in (3, 2, 1):
            if baisse_monde >= cib["baisse_palier_%d" % k]:
                palier = k
                break
    else:
        ko.append("serie WPEA indisponible : paliers de baisse non evalues")
    cible = cib["cible_palier_%d" % palier] if palier else cib["actions"]
    ecart = part_act - cible
    palier_veille = int(veille.get("palier") or 0)
    if palier > palier_veille:
        alertes.append("FORTE BAISSE : MSCI World a %s de son plus haut 1 an -> palier %d, "
                       "nouvelle cible actions %s. A appliquer maintenant (regles §2)."
                       % (pc(-baisse_monde, True), palier, pc(cible)))
    elif palier < palier_veille:
        alertes.append("Le MSCI World est remonte : palier %d -> %d (baisse %s). Retour vers "
                       "65/35 par les versements, sans vente." % (palier_veille, palier, pc(-baisse_monde, True)))
    if abs(ecart) > cib["bande"]:
        alertes.append("Repartition hors bande : actions %s pour une cible de %s (%s). "
                       "Reorienter les prochains versements." % (pc(part_act), pc(cible), pts_txt(ecart)))

    # --- 3. Emergents, Europe, assurance vie, PEA
    em = sum(l["valeur"] * l["actions"] * l["geo"].get("em", 0) for l in lignes)
    part_em = em / actions if actions else 0
    # Alerte emergents seulement quand l ecart sort de la bande (la veille il y etait),
    # et le jour du versement ; sinon l ecart figure dans le rapport.
    hors_bande = abs(part_em - cib["emergents"]) > cib["emergents_bande"]
    try:
        em_veille = float(veille.get("part_em"))
        hors_bande_veille = abs(em_veille - cib["emergents"]) > cib["emergents_bande"]
    except (TypeError, ValueError):
        hors_bande_veille = False
    if hors_bande and (not hors_bande_veille or est_jour_versement(cib)):
        alertes.append("Emergents a %s de la poche actions (cible %s)." % (pc(part_em), pc(cib["emergents"])))
    eu_tot = sum(l["valeur"] * l["actions"] * l["geo"].get("euro", 0) for l in lignes)
    part_eu_tot = eu_tot / actions if actions else 0
    eu = sum(l["valeur"] for l in lignes if l["cle"] == "PCEU.PA")
    part_eu = eu / actions if actions else 0
    if part_eu > cib["europe"] + cib["europe_bande"]:
        alertes.append("Europe (PCEU) a %s de la poche actions, au-dessus de la cible %s : "
                       "reduire sa part des versements." % (pc(part_eu), pc(cib["europe"])))
    av_uc = sum(l["valeur"] for l in lignes if l["env"] == "AV")
    uc_av = av_uc / (av_uc + fonds_euros) if (av_uc + fonds_euros) else 0
    if uc_av < cib["uc_av_min"] or uc_av > cib["uc_av_max"] + 0.02:
        alertes.append("Assurance vie : unites de compte a %s (fourchette %s - %s)."
                       % (pc(uc_av), pc(cib["uc_av_min"]), pc(cib["uc_av_max"])))
    pea_verse = cumul_versements_pea()
    if pea_verse >= cib["alerte_plafond_pea"] * cib["plafond_pea"]:
        alertes.append("PEA : environ %s verses, plus de 90 %% du plafond." % eur(pea_verse))

    # --- 4. Lignes individuelles
    indiv = [l for l in lignes if l["individuelle"]]
    poids_indiv = sum(l["valeur"] for l in indiv) / actions if actions else 0
    if poids_indiv > cib["poche_bonnes_affaires_max"]:
        alertes.append("Actions individuelles : %s de la poche actions (plafond %s)."
                       % (pc(poids_indiv), pc(cib["poche_bonnes_affaires_max"])))
    lignes_txt = []
    for l in sorted(indiv, key=lambda x: -x["valeur"]):
        poids = l["valeur"] / total if total else 0
        lignes_txt.append("- %s (%s) : %s, %s du patrimoine, jour %s"
                          % (l["nom"], l["env"], eur(l["valeur"]), pc(poids), pc(l["var_jour"], True)))
        if l["var_jour"] is not None and abs(l["var_jour"]) >= cib["ligne_mouvement_jour"]:
            alertes.append("%s a bouge de %s aujourd hui : analyse a faire ce soir."
                           % (l["nom"], pc(l["var_jour"], True)))
        if poids > cib["ligne_individuelle_max"]:
            alertes.append("%s pese %s du patrimoine (plafond %s)."
                           % (l["nom"], pc(poids), pc(cib["ligne_individuelle_max"])))

    # --- 5. Bonnes affaires
    cand, sans_fiche = [], 0
    try:
        cand, sans_fiche = candidats(cib)
    except Exception as e:
        ko.append("liste des bonnes affaires indisponible (%s)" % e)
    try:
        with open(os.path.join(DOSSIER, "candidats.json"), encoding="utf-8") as f:
            anciens = json.load(f)
    except Exception:
        anciens = {}
    nouveaux = [c for c in cand if c["tk"] not in anciens]
    mures = [c for c in cand if c["delai_ok"] and not anciens.get(c["tk"], {}).get("delai_ok")]
    for c in nouveaux:
        alertes.append("Nouvelle candidate : %s, %s depuis son plus haut 6 mois, saine "
                       "(%s, marge %s). Delai d un mois apres le dernier choc : %s."
                       % (c["nom"], pc(-c["baisse"], True), levier_txt(c["lev"]), pc(c["marge"]),
                          "atteint" if c["delai_ok"] else "encore %d jours" % (int(cib["ba_delai_jours"]) - c["jours"])))
    for c in mures:
        if c not in nouveaux:
            alertes.append("%s : delai d un mois atteint, analyse avant achat possible." % c["nom"])
    with open(os.path.join(DOSSIER, "candidats.json"), "w", encoding="utf-8") as f:
        json.dump(dict((c["tk"], dict(nom=c["nom"], delai_ok=c["delai_ok"])) for c in cand),
                  f, ensure_ascii=False, indent=1)

    # --- 6. Signaux de fond
    infl, infl_mois = inflation_zone_euro()
    mp = series[SYM_MP]
    mp6, mp12 = perf(mp, 126), perf(mp, 250)
    sig_mp = int(infl is not None and infl > 3.0 and (mp6 or 0) > 0 and (mp12 or 0) > 0)
    em12, monde12 = perf(series[SYM_EM], 250), perf(monde, 250)
    ecart_em = (em12 - monde12) if (em12 is not None and monde12 is not None) else None
    sig_em = 0 if ecart_em is None else (1 if ecart_em > 0.10 else (-1 if ecart_em < -0.10 else 0))
    chg6 = perf(series[SYM_CHANGE], 126)
    n_mp = jours_consecutifs(hist, "sig_mp", sig_mp)
    n_em = jours_consecutifs(hist, "sig_em", sig_em)
    if sig_mp and n_mp == PERSISTANCE:
        alertes.append("Signal matieres premieres allume depuis %d seances : a examiner a la "
                       "prochaine revue mensuelle (palier de 5 points au plus)." % n_mp)
    if sig_em and n_em == PERSISTANCE:
        alertes.append("Signal emergents (%s) allume depuis %d seances : a examiner a la "
                       "prochaine revue mensuelle." % ("surperformance" if sig_em > 0 else "sous-performance", n_em))

    # --- 7. Versement
    if est_jour_versement(cib):
        alertes.append("Jour de versement (%s). Repartition par defaut : WPEA %d, PCEU %d, "
                       "PAASI %d, defensif %d - ajustee par la revue mensuelle de Claude."
                       % (eur(cib["montant_versement"]), cib["versement_wpea"], cib["versement_pceu"],
                          cib["versement_paasi"], cib["versement_defensif"]))

    # --- Historique
    ecrire_historique(hist, dict(
        date=JOUR, part_actions="%.4f" % part_act, cible="%.2f" % cible, palier=palier,
        baisse_monde="" if baisse_monde is None else "%.4f" % baisse_monde,
        part_em="%.4f" % part_em, uc_av="%.4f" % uc_av, sig_mp=sig_mp, sig_em=sig_em,
        inflation="" if infl is None else "%.2f" % infl, nb_candidats=len(cand)))

    # --- Rapport
    env_tot = {}
    for l in lignes:
        env_tot[l["env"]] = env_tot.get(l["env"], 0) + l["valeur"]
    env_tot["AV"] = env_tot.get("AV", 0) + fonds_euros
    r = []
    r.append("# Veille du %s" % AUJ.strftime("%d/%m/%Y"))
    r.append("")
    r.append("## Alertes")
    r += (["- " + a for a in alertes] if alertes else ["- Aucune."])
    r.append("")
    r.append("## Repartition")
    r.append("- Patrimoine consolide : %s (%s)" % (eur(total), ", ".join(
        "%s %s" % (k, eur(v)) for k, v in sorted(env_tot.items()))))
    r.append("- Actions %s / defensif %s ; cible %s%s ; ecart %s"
             % (pc(part_act), pc(1 - part_act), pc(cible),
                (" (palier %d)" % palier) if palier else "", pts_txt(ecart)))
    r.append("- MSCI World (WPEA) : %s depuis son plus haut 1 an" % pc(-baisse_monde if baisse_monde is not None else None, True))
    r.append("- Emergents : %s de la poche actions (cible %s)" % (pc(part_em), pc(cib["emergents"])))
    r.append("- Europe, toutes sources (MSCI World compris) : %s de la poche actions (%s)"
             % (pc(part_eu_tot), eur(eu_tot)))
    r.append("- dont ETF Europe (PCEU) : %s de la poche actions (cible %s, atteinte par les versements)"
             % (pc(part_eu), pc(cib["europe"])))
    r.append("- Assurance vie : unites de compte %s (fourchette %s - %s)"
             % (pc(uc_av), pc(cib["uc_av_min"]), pc(cib["uc_av_max"])))
    r.append("- PEA : environ %s verses sur %s (approximatif : ancrages du 16/06/2026)"
             % (eur(pea_verse), eur(cib["plafond_pea"])))
    r.append("")
    r.append("## Lignes individuelles (%s de la poche actions)" % pc(poids_indiv))
    r += lignes_txt or ["- Aucune."]
    r.append("")
    r.append("## Bonnes affaires candidates (%d)" % len(cand))
    if cand:
        for c in cand[:15]:
            r.append("- %s (%s) : %s depuis le plus haut 6 mois ; dernier choc le %s (%d jours) ; "
                     "%s, marge %s, rentabilite %s ; delai %s%s"
                     % (c["nom"], c["tk"], pc(-c["baisse"], True), c["choc"], c["jours"],
                        levier_txt(c["lev"]), pc(c["marge"]), pc(c["roe"]),
                        "atteint" if c["delai_ok"] else "non atteint",
                        " ; deja en portefeuille" if c["pf"] else ""))
    else:
        r.append("- Aucune valeur ne remplit tous les criteres.")
    if sans_fiche:
        r.append("- %d valeurs en forte baisse sans fondamentaux (relancer « Analyse historique » "
                 "dans telemesure-zone-euro)." % sans_fiche)
    r.append("")
    r.append("## Signaux de fond")
    r.append("- Inflation zone euro : %s (%s)" % (("%.1f %%" % infl).replace(".", ",") if infl is not None else "n.d.", infl_mois or "n.d."))
    r.append("- Matieres premieres (EXXY.DE) : 6 mois %s, 12 mois %s -> signal %s (%d seances)"
             % (pc(mp6, True), pc(mp12, True), "allume" if sig_mp else "eteint", n_mp))
    r.append("- Emergents moins monde, 12 mois : %s -> signal %s (%d seances)"
             % (pc(ecart_em, True), {1: "surperformance", -1: "sous-performance", 0: "neutre"}[sig_em], n_em))
    r.append("- Euro / dollar, 6 mois : %s" % pc(chg6, True))
    if ko:
        r.append("")
        r.append("## Donnees manquantes")
        r += ["- " + k for k in ko]
    texte = "\n".join(r) + "\n"
    for nom in ("derniere.md", "veille-%s.md" % JOUR):
        with open(os.path.join(DOSSIER, nom), "w", encoding="utf-8") as f:
            f.write(texte)
    print(texte)

    if alertes:
        msg = ["Veille du %s" % AUJ.strftime("%d/%m/%Y"), ""]
        msg += ["- " + a for a in alertes]
        msg += ["", "Actions %s / defensif %s (cible %s). MSCI World %s du plus haut."
                % (pc(part_act), pc(1 - part_act), pc(cible),
                   pc(-baisse_monde if baisse_monde is not None else None, True))]
        telegram("\n".join(msg))


if __name__ == "__main__":
    main()
