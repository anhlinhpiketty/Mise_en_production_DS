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
import duckdb
from bs4 import BeautifulSoup

# Import local
import llm

# Chemins relatifs (à changer)
BASE_PATH = 's3://colaslepoutre/Classification_compétences_jocas'
PROMPT_NUM = 's3://colaslepoutre/Classification_compétences_jocas/prompt_num.txt'
PROMPT_THEME = 's3://colaslepoutre/Classification_compétences_jocas/prompt_thematique.txt'
PROMPT_NIV = 's3://colaslepoutre/Classification_compétences_jocas/prompt_niv.txt'
PROMPT_IA = 's3://colaslepoutre/Classification_compétences_jocas/prompt_class_ia.txt'

HISTORY_NORMALIZED = 's3://colaslepoutre/Classification_compétences_jocas/competences_jocas_2019_to_2025_normalized.csv'
HISTORY_NUM = 's3://colaslepoutre/Classification_compétences_jocas/num_competences_jocas_2019_to_2025.csv'
HISTORY_THEME = 's3://colaslepoutre/Classification_compétences_jocas/thematique_num_competences_jocas_2019_to_2025.csv'
HISTORY_NIV = 's3://colaslepoutre/Classification_compétences_jocas/niv_num_competences_jocas_2019_to_2025.csv'
HISTORY_IA = 's3://colaslepoutre/Classification_compétences_jocas/ia_num_competences_jocas_2019_to_2025.csv'

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
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

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
    text = re.sub(r'\\[a-zA-Z]+', ' ', text)
    # Suppression des caractères de contrôle
    text = re.sub(r'[\x00-\x1F\x7F]', ' ', text)
    text = text.lower()
    # Suppression de la ponctuation
    text = re.sub(r'[^\w\s]', ' ', text)
    # Normalisation des espaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text

def classify(skills: List[str]) -> List[Dict[str, Any]]:
    """
    Classifie une liste de compétences en combinant historique et LLM.
    """
    if not isinstance(skills, list):
        return []

    outputs = classify_from_history(skills)

    # Identifier les compétences non trouvées dans l'historique
    remaining_skills = [
        output['label']
        for output in outputs
        if output['categorie'] is None
    ]

    if remaining_skills:
        remaining_outputs = classify_from_llm(remaining_skills)

        # Réinjecter les classifications LLM dans la liste principale
        remaining_iter = iter(remaining_outputs)
        for k, output in enumerate(outputs):
            if output['categorie'] is None:
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
        item['entrée']
        for item in types
        if item.get('cat') == 'compétence numérique'
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
        theme_map = {item['entrée']: item['cat'] for item in theme_results}
        niv_map = {item['entrée']: item['cat'] for item in niv_results}
        ia_map = {item['entrée']: item['cat'] for item in ia_results}

    output: List[Dict[str, Any]] = []
    for item in types:
        entree = item.get('entrée', '')
        categorie = item.get('cat', '')
        is_num = categorie == 'compétence numérique'

        details: Optional[Dict[str, Optional[str]]] = None
        if is_num:
            details = {
                "thematique": theme_map.get(entree),
                "niveau": niv_map.get(entree),
                "categorie_ia": ia_map.get(entree),
            }

        output.append({
            "label": entree,
            "categorie": categorie,
            "details": details
        })

    return output

def classify_from_history(skills: List[str]) -> List[Dict[str, Any]]:
    """
    Recherche des compétences dans l'historique de classifications (DuckDB).
    """
    con = _get_classif_history_connection()
    output: List[Dict[str, Any]] = []

    for skill in skills:
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
            output.append({
                "label": skill,
                "categorie": None,
                "details": None
            })
        else:
            row = result.iloc[0]
            is_num = row['num_cat'] == 'compétence numérique'
            details = {
                "thematique": row['theme_cat'],
                "niveau": row['niv_cat'],
                "categorie_ia": None if row['ia_cat'] == 'Erreur' else row['ia_cat'],
            } if is_num else None
            output.append({
                "label": row['num_entree'],
                "categorie": row['num_cat'],
                "details": details
            })

    return output

def _load_classif_history() -> duckdb.DuckDBPyConnection:
    """
    Charge l'historique de classifications dans une table DuckDB en mémoire.
    """
    con = duckdb.connect()

    con.execute(f"""
        CREATE OR REPLACE SECRET custom_secret_minio (
            TYPE S3,
            KEY_ID '{os.environ["AWS_ACCESS_KEY_ID"]}',
            SECRET '{os.environ["AWS_SECRET_ACCESS_KEY"]}',
            SESSION_TOKEN '{os.environ["AWS_SESSION_TOKEN"]}',
            ENDPOINT '{os.environ["AWS_S3_ENDPOINT"]}',
            URL_STYLE 'path',
            SCOPE '{BASE_PATH}'
        );
    """)

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
