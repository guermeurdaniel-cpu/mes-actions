# -*- coding: utf-8 -*-
"""
supports.py — Lecture du catalogue des supports (supports.txt).

Ce petit module est partage par scraper.py et par patrimoine.py, pour que les
deux voient exactement la meme liste de valeurs que le tableau de bord. Il n y a
donc qu un seul endroit ou declarer une valeur : supports.txt.

Format lu (voir l en-tete de supports.txt pour la documentation complete) :

    [Intitule du support]
    cle       = QS0009080175      ISIN, ou symbole Yahoo si la valeur est cotee
    enveloppe = PEG               PEG, PEA, AV ou LIV (livrets)
    source    = amundi-ee         yahoo, amundi-ee, amundi-fr, abcbourse, boursier, fixe
    url       = https://...       uniquement pour abcbourse et boursier
    actions   = 1.00              part investie en actions, entre 0 et 1
    geo       = monde 0.50 + euro 0.50
    taux      = 2026-01-01 1.70 + 2026-02-01 1.50    livrets : taux annuel en %, par date d effet
    frais     = 0.1875            assurance vie (UC) : frais de gestion en % par trimestre

Les lignes vides et celles commencant par # sont ignorees.
"""

import calendar
import re

FICHIER = "supports.txt"
ENVELOPPES_VALIDES = ("PEG", "PEA", "AV", "LIV")
SOURCES_VALIDES = ("yahoo", "amundi-ee", "amundi-fr", "abcbourse", "boursier", "fixe")


def _nombre(txt):
    """Accepte la virgule decimale francaise. Chaine vide -> 0.0."""
    t = (txt or "").strip().replace(",", ".")
    return float(t) if t else 0.0


def _geo(txt):
    """'monde 0.50 + euro 0.50' -> {'monde': 0.5, 'euro': 0.5, 'em': 0.0}"""
    g = {"monde": 0.0, "euro": 0.0, "em": 0.0}
    for part in (txt or "").split("+"):
        mots = part.strip().split()
        if not mots:
            continue
        nom = mots[0].lower()
        poids = _nombre(mots[1]) if len(mots) > 1 else 1.0
        if nom.startswith("monde"):
            g["monde"] += poids
        elif nom.startswith("euro"):
            g["euro"] += poids
        elif nom.startswith("emerg"):
            g["em"] += poids
    return g


def _taux(txt):
    """'2026-01-01 1.70 + 2026-02-01 1.50' -> [('2026-01-01', 1.7), ('2026-02-01', 1.5)]"""
    liste = []
    for part in (txt or "").split("+"):
        mots = part.strip().split()
        if not mots:
            continue
        if len(mots) != 2 or not re.match(r"^\d{4}-\d{2}-\d{2}$", mots[0]):
            raise RuntimeError("taux mal ecrit : '%s' (attendu AAAA-MM-JJ taux)" % part.strip())
        liste.append((mots[0], _nombre(mots[1])))
    return sorted(liste)


def lire(chemin=FICHIER):
    """Renvoie la liste des supports, dans l ordre du fichier.

    Chaque support est un dict : nom, cle, enveloppe, source, url, actions, geo.
    Leve une exception explicite si le fichier est incoherent : mieux vaut un
    arret net qu un patrimoine calcule sur une valeur manquante.
    """
    supports = []
    courant = None

    with open(chemin, "r", encoding="utf-8-sig") as f:
        for num, brut in enumerate(f, start=1):
            ligne = brut.strip()
            if not ligne or ligne.startswith("#"):
                continue

            titre = re.match(r"^\[(.+)\]$", ligne)
            if titre:
                courant = {
                    "nom": titre.group(1).strip(), "cle": "", "enveloppe": "",
                    "source": "", "url": "", "actions": 0.0,
                    "geo": {"monde": 0.0, "euro": 0.0, "em": 0.0},
                    "taux": [], "frais": 0.0,
                }
                supports.append(courant)
                continue

            if "=" not in ligne or courant is None:
                raise RuntimeError("%s ligne %d : hors bloc ou sans signe = " % (chemin, num))

            champ, _, valeur = ligne.partition("=")
            champ = champ.strip().lower()
            valeur = valeur.strip()

            if champ in ("cle", "clé"):
                courant["cle"] = valeur
            elif champ == "enveloppe":
                courant["enveloppe"] = valeur.upper()
            elif champ == "source":
                courant["source"] = valeur.lower()
            elif champ == "url":
                courant["url"] = valeur
            elif champ == "actions":
                courant["actions"] = _nombre(valeur)
            elif champ == "geo":
                courant["geo"] = _geo(valeur)
            elif champ == "taux":
                courant["taux"] = _taux(valeur)
            elif champ == "frais":
                courant["frais"] = _nombre(valeur)
            else:
                raise RuntimeError("%s ligne %d : champ inconnu '%s'" % (chemin, num, champ))

    # Controles de coherence
    vues = set()
    for s in supports:
        ou = "[%s]" % s["nom"]
        if not s["cle"]:
            raise RuntimeError("%s : pas de cle" % ou)
        if s["cle"] in vues:
            raise RuntimeError("%s : cle en double (%s)" % (ou, s["cle"]))
        vues.add(s["cle"])
        if s["enveloppe"] not in ENVELOPPES_VALIDES:
            raise RuntimeError("%s : enveloppe inconnue '%s'" % (ou, s["enveloppe"]))
        if s["source"] not in SOURCES_VALIDES:
            raise RuntimeError("%s : source inconnue '%s'" % (ou, s["source"]))
        if s["source"] in ("abcbourse", "boursier") and not s["url"]:
            raise RuntimeError("%s : source %s sans url" % (ou, s["source"]))

    if not supports:
        raise RuntimeError("%s : aucun support declare" % chemin)
    return supports


def cotes(supports):
    """Symboles Yahoo des valeurs cotees, dans l ordre du catalogue."""
    return [s["cle"] for s in supports if s["source"] == "yahoo"]


def fonds(supports):
    """Supports dont la valeur doit etre recuperee par le scraper (non cotes).
    Les livrets (source fixe) n ont pas de valeur a recuperer : exclus."""
    return [s for s in supports if s["source"] not in ("yahoo", "fixe")]


def fixes(supports):
    """Cles des supports a valeur fixe (livrets) : solde du journal + interets courus."""
    return [s["cle"] for s in supports if s["source"] == "fixe"]


# ----------------------------------------------------------------------------
#  FRAIS DE GESTION DES UNITES DE COMPTE (assurance vie)
# ----------------------------------------------------------------------------
#  L assureur preleve chaque trimestre un pourcentage des parts detenues, en
#  diminuant leur nombre. On reconstitue ces prelevements au dernier jour de
#  chaque trimestre echu : parts detenues ce jour-la (mouvements dates de ce jour
#  inclus, prelevements precedents deduits) x taux. Meme calcul que index.html.
FINS_TRIMESTRE = ("-03-31", "-06-30", "-09-30", "-12-31")


def frais_trimestriels(taux_pct, mouvements, jusqua):
    """mouvements : [(date AAAA-MM-JJ, quantite), ...] d un seul support.
    Renvoie les prelevements [(date, quantite negative), ...] jusqu a jusqua inclus."""
    if not taux_pct or not mouvements:
        return []
    f = taux_pct / 100.0
    dates = sorted(d for d, _ in mouvements if d)
    if not dates:
        return []
    out = []
    for annee in range(int(dates[0][:4]), int(jusqua[:4]) + 1):
        for fin in FINS_TRIMESTRE:
            d = "%d%s" % (annee, fin)
            if d < dates[0]:
                continue
            if d > jusqua:
                return out
            detenu = sum(q for dm, q in mouvements if not dm or dm <= d)
            detenu += sum(q for _, q in out)
            if detenu > 1e-6:
                out.append((d, -detenu * f))
    return out


def par_intitule(supports):
    """Intitule lisible -> cle. C est la correspondance utilisee par apports.csv."""
    return dict((s["nom"], s["cle"]) for s in supports)


# -----------------------------------------------------------------------------
#  LIVRETS : interets courus de l annee en cours, regle des quinzaines
# -----------------------------------------------------------------------------
#  Un livret rapporte par quinzaine (du 1er au 15, du 16 a la fin du mois) :
#    - un versement porte interet a partir du 1er ou du 16 qui SUIT sa date ;
#    - un retrait cesse de porter interet des le debut de SA quinzaine ;
#    - un solde date du 1er janvier (ou d avant) est en place des la 1re quinzaine.
#  Interet d une quinzaine = solde x taux annuel en vigueur a son debut / 24.
#  Seules les quinzaines ACHEVEES a la date demandee sont comptees : c est ce que
#  la banque versera au 31 decembre. Les interets d une annee passee doivent
#  etre saisis dans apports.csv (quantite = montant, prix 0) une fois credites.
#  Meme calcul que interetsCourus() dans index.html : les deux doivent rester
#  identiques.

def _quinzaines(annee):
    """Les 24 quinzaines d une annee : liste de (debut, fin) en AAAA-MM-JJ."""
    q = []
    for m in range(1, 13):
        der = calendar.monthrange(annee, m)[1]
        q.append(("%04d-%02d-01" % (annee, m), "%04d-%02d-15" % (annee, m)))
        q.append(("%04d-%02d-16" % (annee, m), "%04d-%02d-%02d" % (annee, m, der)))
    return q


def interets_courus(taux, mouvements, date):
    """Interets acquis depuis le 1er janvier de l annee de `date`, en EUR.

    taux        liste (date d effet, taux annuel en %) triee
    mouvements  liste (date AAAA-MM-JJ, quantite) du support
    date        AAAA-MM-JJ
    """
    if not taux:
        return 0.0
    annee = int(date[:4])
    debut_annee = "%04d-01-01" % annee
    total = 0.0
    for deb, fin in _quinzaines(annee):
        if fin >= date:                 # quinzaine pas encore achevee
            break
        solde = 0.0
        for d, q in mouvements:
            if q > 0 and (d < deb or d <= debut_annee):
                solde += q              # versement : compte s il precede la quinzaine
            elif q < 0 and d <= fin:
                solde += q              # retrait : penalise toute sa quinzaine
        t = 0.0
        for d_effet, tx in taux:
            if d_effet <= deb:
                t = tx
        total += max(solde, 0.0) * t / 100.0 / 24.0
    return total


def valeur_livret(taux, mouvements, date):
    """Solde du journal a `date` plus interets courus de l annee."""
    solde = sum(q for d, q in mouvements if d <= date)
    return solde + interets_courus(taux, mouvements, date)
