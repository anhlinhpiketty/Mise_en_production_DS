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
S3_MODEL_PATH = os.environ['S3_PATH']+(
    "/NER_model"
)
LOCAL_MODEL_PATH = (
    "model_spacy_trained"
)


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
        client_kwargs={'endpoint_url': 'https://'+'minio.lab.sspcloud.fr'},
        key = os.environ["AWS_ACCESS_KEY_ID"], 
        secret = os.environ["AWS_SECRET_ACCESS_KEY"], 
        token = os.environ["AWS_SESSION_TOKEN"])

    if not os.path.exists(LOCAL_MODEL_PATH):
        print("Téléchargement du modèle...")
        fs.get(S3_MODEL_PATH, LOCAL_MODEL_PATH, recursive=True)
        print("Téléchargement terminé.")
    else:
        print("Modèle déjà présent localement, on passe le téléchargement.")

    nlp = spacy.load(LOCAL_MODEL_PATH)
    return nlp
