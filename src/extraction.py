"""
Module d'extraction de compétences à partir de descriptions d'offres d'emploi.
Utilise un modèle spaCy NER entraîné pour identifier et extraire les compétences.
"""

import os
import spacy
from dotenv import load_dotenv
import s3fs

load_dotenv()
model_secret = os.environ["MODEL_SECRET"]

# CONFIG
BUCKET_NAME = "projet-jocas-prod"
S3_MODEL_PATH = (
    "projet-jocas-prod/Data_etudes/Etude_num/modeles_NER_spacy/camembertav2_skill_only"
)
LOCAL_MODEL_PATH = (
    "/home/onyxia/work/model_spacy_trained"  # Où le télécharger sur le disque
)

SOURCE_PATH = (
    "s3://projet-jocas-prod/JOCAS_V3_NO_DUP_NO_PARTNER_NO_JIT/annee=2025/*/*/*.parquet"
)

S3_ENDPOINT_URL = "https://" + os.environ["AWS_S3_ENDPOINT"]


def extract_skills_from(desc_offre: str) -> list[str]:
    """
    Effectue l'inférence pour extraire les compétences d'une description d'offre d'emploi.

    Args:
        desc_offre (str): Description d'une offre d'emploi.

    Returns:
        list[str]: Liste des compétences extraites.
    """
    nlp = import_model()
    with nlp.select_pipes(enable=["transformer", "ner"]):
        doc = nlp(desc_offre)
    skills = [e.text for e in doc.ents]
    return skills

def import_model() -> spacy.language.Language:
    """
    Charge le modèle spaCy depuis un bucket S3 ou localement s'il est déjà présent.

    Returns:
        spacy.language.Language: Modèle spaCy chargé et prêt à l'emploi.
    """
    fs = s3fs.S3FileSystem(
        endpoint_url=S3_ENDPOINT_URL,
        key="jocas-prod",
        secret=model_secret,
    )
    if not os.path.exists(LOCAL_MODEL_PATH):
        print("Téléchargement du modèle...")
        fs.get(S3_MODEL_PATH, LOCAL_MODEL_PATH, recursive=True)
        print("Téléchargement terminé.")
    else:
        print("Modèle déjà présent localement, on passe le téléchargement.")

    nlp = spacy.load(LOCAL_MODEL_PATH)
    return nlp
