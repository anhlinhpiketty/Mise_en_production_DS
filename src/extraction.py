"""
Module d'extraction de compétences à partir de descriptions d'offres d'emploi.
Utilise un modèle spaCy NER entraîné pour identifier et extraire les compétences.
"""

import os
import logging
import spacy
from dotenv import load_dotenv
import s3fs

from src.logging_config import setup_logging

load_dotenv(override=True)

# CONFIG
S3_MODEL_PATH = os.environ["S3_PATH"] + ("/NER_model")
LOCAL_MODEL_PATH = "model_spacy_trained"

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def extract_skills_from(desc_offre: str) -> list[str]:
    """
    Effectue l'inférence pour extraire les compétences d'une description d'offre d'emploi.

    Args:
        desc_offre (str): Description d'une offre d'emploi.

    Returns:
        list[str]: Liste des compétences extraites.
    """
    try:
        nlp = import_model()
        with nlp.select_pipes(enable=["transformer", "ner"]):
            doc = nlp(desc_offre)
        skills = [e.text for e in doc.ents]
        logger.info("%d compétence(s) extraite(s)", len(skills))
        return skills
    except Exception:
        logger.exception("Erreur lors de l'extraction des compétences")
        return []


def import_model() -> spacy.language.Language:
    """
    Charge le modèle spaCy depuis un bucket S3 ou localement s'il est déjà présent.

    Returns:
        spacy.language.Language: Modèle spaCy chargé et prêt à l'emploi.
    """
    fs = s3fs.S3FileSystem(
        client_kwargs={"endpoint_url": "https://" + os.environ['AWS_S3_ENDPOINT']}
    )

    if not os.path.exists(LOCAL_MODEL_PATH):
        logger.info("Téléchargement du modèle depuis S3 : %s", S3_MODEL_PATH)
        try:
            fs.get(S3_MODEL_PATH, LOCAL_MODEL_PATH, recursive=True)
        except Exception:
            logger.warning("Erreur dans le téléchargement du model d'extraction")
            raise
        logger.info("Téléchargement terminé")
    else:
        logger.debug("Modèle déjà présent localement, téléchargement ignoré")

    try:
        nlp = spacy.load(LOCAL_MODEL_PATH)
        logger.info("Modèle spaCy chargé depuis %s", LOCAL_MODEL_PATH)
        return nlp
    except Exception:
        logger.exception(
            "Impossible de charger le modèle spaCy depuis %s", LOCAL_MODEL_PATH
        )
        raise
