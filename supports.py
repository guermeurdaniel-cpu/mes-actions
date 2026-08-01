# -*- coding: utf-8 -*-
"""
supports.py — Lecture du catalogue des supports (supports.txt).

Ce petit module est partage par scraper.py et par patrimoine.py, pour que les
deux voient exactement la meme liste de valeurs que le tableau de bord. Il n y a
donc qu un seul endroit ou declarer une valeur : supports.txt.

Format lu (voir l en-tete de supports.txt pour la documentation complete) :

    [Intitule du support]
    cle       = QS0009080175      ISIN, ou symbole Yahoo si la valeur est cotee
    enveloppe = PEG               PEG, PEA ou AV
    source    = amundi-ee         yahoo, amundi-ee, amundi-fr, abcbourse, boursier
    url       = https://...       uniquement pour abcbourse et boursier
    actions   = 1.00              part investie en actions, entre 0 et 1
    geo       = monde 0.50 + euro 0.50

Les lignes vides et celles commencant par # sont ignorees.
"""

import re

FICHIER = "supports.txt"
ENVELOPPES_VALIDES = ("PEG", "PEA", "AV")
SOURCES_VALIDES = ("yahoo", "amundi-ee", "amundi-fr", "abcbourse", "boursier")


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
    """Supports dont la valeur doit etre recuperee par le scraper (non cotes)."""
    return [s for s in supports if s["source"] != "yahoo"]


def par_intitule(supports):
    """Intitule lisible -> cle. C est la correspondance utilisee par apports.csv."""
    return dict((s["nom"], s["cle"]) for s in supports)
