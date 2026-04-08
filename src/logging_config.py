"""Configure le logging pour l'application."""

import logging


def setup_logging():
    """Configure le logging pour l'application.

    Initialise un format personnalisé, un fichier de log et un affichage console.
    Réduit le niveau de log des bibliothèques tierces bruyantes à WARNING.
    """
    logging.basicConfig(
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M",
        level=logging.DEBUG,
        handlers=[logging.FileHandler("recording.log"), logging.StreamHandler()],
    )

    for noisy_logger in (
        "boto3",
        "botocore",
        "aiobotocore",
        "s3fs",
        "s3transfer",
        "urllib3",
        "httpcore",
        "httpx",
        "openai",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
