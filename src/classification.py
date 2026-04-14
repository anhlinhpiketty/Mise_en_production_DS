"""
Module de classification de compétences.

Classifie chaque compétence en s'appuyant d'abord sur un historique de
classifications passées (via DuckDB), puis en appelant un LLM pour les
compétences inconnues.
"""

import html
import re
from typing import List, Dict, Optional, Any
import os
import logging

import duckdb
from bs4 import BeautifulSoup
import s3fs
from dotenv import load_dotenv

# Import local
from src import llm
from src.logging_config import setup_logging


load_dotenv(override=True)
S3_PATH = os.environ["S3_PATH"]

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


# Chemins relatifs (à changer)
PROMPT_NUM = S3_PATH + "/prompt_num.txt"
PROMPT_THEME = S3_PATH + "/prompt_thematique.txt"
PROMPT_NIV = S3_PATH + "/prompt_niv.txt"
PROMPT_IA = S3_PATH + "/prompt_class_ia.txt"

HISTORY_NORMALIZED = S3_PATH + "/competences_jocas_2019_to_2025_normalized.csv"
HISTORY_NUM = S3_PATH + "/num_competences_jocas_2019_to_2025.csv"
HISTORY_THEME = S3_PATH + "/thematique_num_competences_jocas_2019_to_2025.csv"
HISTORY_NIV = S3_PATH + "/niv_num_competences_jocas_2019_to_2025.csv"
HISTORY_IA = S3_PATH + "/ia_num_competences_jocas_2019_to_2025.csv"

# Variable globale pour la connexion DuckDB
_DUCKDB_CONNECTION = None


def _get_classif_history_connection() -> duckdb.DuckDBPyConnection:
    """
    Retourne une connexion DuckDB partagée pour l'historique de classification.
    Crée la connexion si elle n'existe pas encore.
    """
    global _DUCKDB_CONNECTION
    if _DUCKDB_CONNECTION is None:
        _DUCKDB_CONNECTION = _load_classif_history()
    return _DUCKDB_CONNECTION


def read_txt(path: str) -> str:
    """Lit et retourne le contenu d'un fichier texte."""
    fs = s3fs.S3FileSystem(
        client_kwargs={"endpoint_url": "https://" + os.environ['AWS_S3_ENDPOINT']},
        anon=True
    )
    with fs.open(path) as f:
        return f.read().decode("utf-8")


def normalize(text: str) -> str:
    """
    Normalise un libellé de compétence pour la comparaison :
    décode les entités HTML, supprime les balises, met en minuscules,
    et retire la ponctuation et les espaces superflus.
    """
    if not isinstance(text, str):
        return ""

    text = html.unescape(text)
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text(separator=" ")

    # Suppression des séquences LaTeX résiduelles
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    # Suppression des caractères de contrôle
    text = re.sub(r"[\x00-\x1F\x7F]", " ", text)
    text = text.lower()
    # Suppression de la ponctuation
    text = re.sub(r"[^\w\s]", " ", text)
    # Normalisation des espaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def classify(skills: List[str]) -> List[Dict[str, Any]]:
    """
    Classifie une liste de compétences en combinant historique et LLM.
    """
    if not isinstance(skills, list):
        logger.warning("classify() appelé avec un type invalide : %s", type(skills))
        return []

    logger.info("Classification de %d compétence(s)", len(skills))
    outputs = classify_from_history(skills)

    remaining_skills = [o["label"] for o in outputs if o["categorie"] is None]

    if remaining_skills:
        logger.info(
            "%d compétence(s) non trouvée(s) en historique, appel LLM",
            len(remaining_skills),
        )
        remaining_outputs = classify_from_llm(remaining_skills)

        # Réinjecter les classifications LLM dans la liste principale
        remaining_iter = iter(remaining_outputs)
        for k, output in enumerate(outputs):
            if output["categorie"] is None:
                outputs[k] = next(remaining_iter)

    return outputs


def classify_from_llm(skills: List[str]) -> List[Dict[str, Any]]:
    """
    Classifie une liste de compétences via des appels LLM successifs.
    """
    prompt_num = read_txt(PROMPT_NUM)
    prompt_theme = read_txt(PROMPT_THEME)
    prompt_niv = read_txt(PROMPT_NIV)
    prompt_ia = read_txt(PROMPT_IA)

    # Étape 1 — classification type de compétence
    types = llm.call(skills, prompt_num)

    # Extraire les compétences numériques
    num_entries = [
        item["entrée"] for item in types if item.get("cat") == "compétence numérique"
    ]

    theme_map: Dict[str, str] = {}
    niv_map: Dict[str, str] = {}
    ia_map: Dict[str, str] = {}

    if num_entries:
        # Étapes 2, 3, 4 — sous-classifications des compétences numériques
        theme_results = llm.call(num_entries, prompt_theme)
        niv_results = llm.call(num_entries, prompt_niv)
        ia_results = llm.call(num_entries, prompt_ia)

        # Indexation par libellé pour un accès rapide
        theme_map = {item["entrée"]: item["cat"] for item in theme_results}
        niv_map = {item["entrée"]: item["cat"] for item in niv_results}
        ia_map = {item["entrée"]: item["cat"] for item in ia_results}

    output: List[Dict[str, Any]] = []
    for item in types:
        entree = item.get("entrée", "")
        categorie = item.get("cat", "")
        is_num = categorie == "compétence numérique"

        details: Optional[Dict[str, Optional[str]]] = None
        if is_num:
            details = {
                "thematique": theme_map.get(entree),
                "niveau": niv_map.get(entree),
                "categorie_ia": ia_map.get(entree),
            }

        output.append({"label": entree, "categorie": categorie, "details": details})

    return output


def classify_from_history(skills: List[str]) -> List[Dict[str, Any]]:
    """
    Recherche des compétences dans l'historique de classifications (DuckDB).
    """
    try:
        con = _get_classif_history_connection()
    except Exception:
        logger.exception("Impossible d'initialiser la connexion DuckDB")
        return [{"label": s, "categorie": None, "details": None} for s in skills]

    output = []

    for skill in skills:
        try:
            normalized_skill = normalize(skill).replace("'", "''")  # échappement SQL

            query = f"""
                SELECT
                    norm_label,
                    num_entree,
                    num_cat,
                    theme_cat,
                    niv_cat,
                    ia_cat
                FROM classif_history
                WHERE norm_label = '{normalized_skill}'
                LIMIT 1
            """

            result = con.sql(query).df()

            if result.empty:
                # Compétence jamais classifiée
                output.append({"label": skill, "categorie": None, "details": None})
            else:
                row = result.iloc[0]
                is_num = row["num_cat"] == "compétence numérique"
                details = (
                    {
                        "thematique": row["theme_cat"],
                        "niveau": row["niv_cat"],
                        "categorie_ia": None
                        if row["ia_cat"] == "Erreur"
                        else row["ia_cat"],
                    }
                    if is_num
                    else None
                )
                output.append(
                    {
                        "label": row["num_entree"],
                        "categorie": row["num_cat"],
                        "details": details,
                    }
                )
        except Exception:
            logger.exception(
                "Erreur lors de la requête DuckDB pour la compétence : %s", skill
            )
            output.append({"label": skill, "categorie": None, "details": None})

    return output


def _load_classif_history() -> duckdb.DuckDBPyConnection:
    """
    Charge l'historique de classifications dans une table DuckDB en mémoire.
    """
    con = duckdb.connect()

    con.sql(f"""
        CREATE VIEW classif_history AS
        SELECT DISTINCT ON (norm.clean)
            norm.clean AS norm_label,
            num.original AS num_original,
            num.entrée AS num_entree,
            num.cat AS num_cat,
            theme.original AS theme_original,
            theme.cat AS theme_cat,
            niv.original AS niv_original,
            niv.cat AS niv_cat,
            ia.original AS ia_original,
            ia.cat AS ia_cat
        FROM read_csv('{HISTORY_NORMALIZED}') AS norm
        LEFT JOIN read_csv('{HISTORY_NUM}') AS num
            ON norm.competence_normalisee = num.original
        LEFT JOIN read_csv('{HISTORY_THEME}') AS theme
            ON num.entrée = theme.original
        LEFT JOIN read_csv('{HISTORY_NIV}') AS niv
            ON num.entrée = niv.original
        LEFT JOIN read_csv('{HISTORY_IA}') AS ia
            ON num.entrée = ia.original
    """)

    return con
