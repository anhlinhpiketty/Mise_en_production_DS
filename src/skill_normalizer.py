"""
skill_normalizer.py
===================

Module de normalisation de compétences textuelles en français.

Fonctionnalités :
- Nettoyage HTML et caractères parasites
- Normalisation unicode et lowercase
- Lemmatisation avec spaCy
- Optimisation via traitement des valeurs uniques
- Logging configurable

Exemple d'utilisation :

    from skill_normalizer import SkillNormalizer
    import pandas as pd

    df = pd.read_csv("input.csv")

    normalizer = SkillNormalizer()
    df_norm, lemma_map = normalizer.normalize_dataframe(df, column="compétence")

"""

# ---------------------------------------------------
# IMPORTS
# ---------------------------------------------------

import html
from setup_logging import setup_logger
import logging
import re
from typing import Dict, List, Tuple

import pandas as pd
import spacy
from bs4 import BeautifulSoup


# ---------------------------------------------------
# SKILL NORMALIZER
# ---------------------------------------------------

class SkillNormalizer:
    """
    Classe principale de normalisation des compétences.

    Pipeline :
    - suppression HTML
    - nettoyage caractères spéciaux
    - normalisation lowercase
    - lemmatisation spaCy
    - optimisation via traitement des valeurs uniques
    """

    def __init__(
        self,
        model_name: str = "fr_core_news_md",
        batch_size: int = 1000,
        n_process: int = -1
    ):
        """
        Initialise le normalizer.

        Parameters
        ----------
        model_name : str
            Nom du modèle spaCy
        batch_size : int
            Taille des batches spaCy
        n_process : int
            Nombre de processus (-1 = tous les CPU)
        """

        self.batch_size = batch_size
        self.n_process = n_process
        setup_logger("log_skill_normalization.log")

        logging.info(f"Chargement modèle spaCy : {model_name}")

        self.nlp = spacy.load(
            model_name,
            disable=["ner", "parser"]
        )

        self.nlp.max_length = 3_000_000

        logging.info("Modèle spaCy chargé")

    # ---------------------------------------------------
    # HTML CLEANING
    # ---------------------------------------------------

    @staticmethod
    def strip_html(text: str) -> str:
        """
        Supprime le HTML et décode les entités.

        Parameters
        ----------
        text : str

        Returns
        -------
        str
        """

        if not isinstance(text, str):
            return ""

        text = html.unescape(text)
        soup = BeautifulSoup(text, "html.parser")

        return soup.get_text(separator=" ")

    # ---------------------------------------------------
    # TEXT CLEANING
    # ---------------------------------------------------

    def clean_series(self, series: pd.Series) -> pd.Series:
        """
        Nettoyage vectorisé d'une série pandas.

        Parameters
        ----------
        series : pd.Series

        Returns
        -------
        pd.Series
        """

        logging.info("Nettoyage vectorisé du texte")

        return (
            series
            .fillna("")
            .map(self.strip_html)
            .str.replace(r"\\[a-zA-Z]+", " ", regex=True)
            .str.replace(r"[\x00-\x1F\x7F]", " ", regex=True)
            .str.lower()
            .str.replace(r"[^\w\s]", " ", regex=True)
            .str.replace(r"\s+", " ", regex=True)
            .str.strip()
        )

    # ---------------------------------------------------
    # LEMMATIZATION
    # ---------------------------------------------------

    def lemmatize_list(self, texts: List[str]) -> List[str]:
        """
        Lemmatisation batchée optimisée.

        Parameters
        ----------
        texts : List[str]

        Returns
        -------
        List[str]
        """

        logging.info(f"Lemmatisation de {len(texts)} textes")

        lemmas = []

        for doc in self.nlp.pipe(
            texts,
            batch_size=self.batch_size,
            n_process=self.n_process
        ):

            tokens = [
                token.lemma_
                for token in doc
                if not token.is_stop
                and not token.is_punct
                and token.lemma_.strip()
            ]

            lemmas.append(" ".join(tokens))

        return lemmas

    # ---------------------------------------------------
    # NORMALIZATION PIPELINE
    # ---------------------------------------------------

    def normalize_dataframe(
        self,
        df: pd.DataFrame,
        column: str
    ) -> Tuple[pd.DataFrame, Dict[str, str]]:
        """
        Normalise une colonne de dataframe.

        Parameters
        ----------
        df : pd.DataFrame
        column : str
            Nom de la colonne à normaliser

        Returns
        -------
        df : pd.DataFrame
            DataFrame enrichi
        lemma_map : Dict[str, str]
            Mapping clean -> lemma
        """

        logging.info("Début normalisation")

        df = df.copy()

        # Nettoyage
        df["clean"] = self.clean_series(df[column])

        # Unique values optimisation
        logging.info("Extraction des valeurs uniques")

        unique_clean = df["clean"].drop_duplicates()

        # Lemmatisation
        unique_lemmas = self.lemmatize_list(unique_clean.tolist())

        lemma_map = dict(zip(unique_clean, unique_lemmas))

        # Mapping final
        df["competence_normalisee"] = df["clean"].map(lemma_map)

        logging.info("Normalisation terminée")

        return df, lemma_map
