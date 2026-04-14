"""
Module d'appel LLM via l'API compatible OpenAI.

Fournit une fonction `call` pour envoyer une liste de compétences à un modèle
de langage avec un prompt système, et retourner les objets JSON parsés.
"""

import re
import json
import os
from typing import List
import logging

from openai import OpenAI
from dotenv import load_dotenv

from src.logging_config import setup_logging

load_dotenv(override=True)

BASE_URL = os.environ.get("BASE_URL", "")

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


def call(competences: List[str], system_prompt: str) -> List[dict]:
    """
    Envoie une liste de compétences à un LLM et retourne les objets JSON parsés.

    Args:
        competences: Liste de libellés de compétences à classifier.
        system_prompt: Prompt système décrivant la tâche de classification.

    Returns:
        Liste de dictionnaires JSON extraits de la réponse du modèle.
        Les blocs JSON invalides sont ignorés avec un avertissement.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(competences, ensure_ascii=False)},
    ]

    logger.debug("Appel LLM pour %d compétence(s)", len(competences))

    try:
        client = _create_client(api_key=os.environ["API_KEY"], base_url=BASE_URL)
        response = client.chat.completions.create(
            model=os.environ["MODEL_NAME"],
            messages=messages,
            temperature=float(os.environ.get("TEMPERATURE", 0.0)),
        )
    except Exception:
        logger.exception("Échec de l'appel LLM")
        return []

    text = response.choices[0].message.content
    json_blocks = re.findall(r"\{.*?\}", text, re.DOTALL)

    parsed = []
    for block in json_blocks:
        try:
            parsed.append(json.loads(block))
        except json.JSONDecodeError:
            logger.warning("Bloc JSON invalide ignoré : %.80s...", block)

    logger.debug(
        "%d objet(s) JSON parsé(s) sur %d bloc(s)", len(parsed), len(json_blocks)
    )
    return parsed


def _create_client(api_key: str, base_url: str) -> OpenAI:
    """
    Crée un client OpenAI pointant vers OpenAI natif ou un endpoint compatible.

    Args:
        api_key: Clé d'API à utiliser.
        base_url: URL de base de l'API. Passer une chaîne vide ou "openai"
                  pour utiliser l'endpoint OpenAI officiel.

    Returns:
        Instance configurée du client OpenAI.
    """
    if not base_url or base_url.lower() == "openai":
        return OpenAI(api_key=api_key)
    return OpenAI(api_key=api_key, base_url=base_url)
