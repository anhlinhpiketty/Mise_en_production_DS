import pandas as pd
import dask
import s3fs
import os
import time
import dask
import duckdb
import dask.dataframe as dd
from dask.distributed import Client
import time
import dask.dataframe as dd
import ast
from setup_logging import setup_logger 
import logging 

def get_jocas_ddf(path, logging_path="logs.log", memory_limit='32GB', n_workers=10, threads_per_worker=3):
    setup_logger(logging_path)

    logging.info("Configuration Dask Client...")
    S3_ENDPOINT_URL = "https://" + os.environ["AWS_S3_ENDPOINT"] #  on récupère l'url du stockage s3
    fs = s3fs.S3FileSystem(endpoint_url= S3_ENDPOINT_URL, key='jocas-prod', secret="")
    client = Client(dashboard_address='0.0.0.0:5000',memory_limit=memory_limit,n_workers=n_workers,threads_per_worker=threads_per_worker)

    # Chemin d'accès des données

    logging.info("Lecture des données...")
    jocas = dd.read_parquet(
        path,
        filesystem=fs,
        engine='pyarrow',
    )

    return jocas

def get_jocas_duckdb_con(path='s3://colaslepoutre/Jocas/JOCAS_WITH_SKILLS_CLASSIFIED_WEIGHTED', logging_path="logs.log"):
    start_time = time.time()
    setup_logger(logging_path)
    conn = duckdb.connect() #On établit une connexion au moteur DuckDB

    conn.execute(f"""
    CREATE OR REPLACE SECRET custom_secret_minio (
        TYPE S3,
        KEY_ID '{os.environ["AWS_ACCESS_KEY_ID"]}',
        SECRET '{os.environ["AWS_SECRET_ACCESS_KEY"]}',
        SESSION_TOKEN '{os.environ["AWS_SESSION_TOKEN"]}',
        ENDPOINT '{os.environ["AWS_S3_ENDPOINT"]}',
        URL_STYLE 'path',
        SCOPE '{path}'
    );
    """)

    # On crée une "vue" qui pointe vers les données, pour pouvoir y faire facilement référence par la suite
    conn.sql(f"""
            CREATE VIEW jocas AS 
                SELECT * FROM read_parquet(
                    '{path}/annee=*/mois=*/jour=*/*.parquet',
                    hive_partitioning=True,
                    union_by_name=True
                    )
            """);
    logging.info('Jocas View chargée')
    
    return conn

def add_comp_cat(
    df_jocas,                  # DataFrame principal
    df_comp_cat,               # DataFrame de correspondance avec les catégories
    new_col_name='num_cat',    # Nom de la nouvelle colonne à créer dans df_jocas
    col_jocas='entree_cleanee_NER',  # Colonne du DataFrame principal à comparer
    col_comp_cat='entrée',          # Colonne de df_comp_cat à comparer
    col_cat='cat'                    # Colonne des catégories dans df_comp_cat
):
    """
    Ajoute une colonne de catégories à df_jocas à partir d'un DataFrame de correspondance df_comp_cat.

    - Explose les listes dans col_jocas pour avoir une ligne par élément.
    - Déduplique df_comp_cat pour ne garder qu'une ligne par 'entrée', préférant les valeurs non-NaN.
    - Merge les deux DataFrames.
    - Regroupe par ligne originale pour reconstruire les listes de catégories.
    - Remplace les NaN par None.
    """
    
    # Exploser les listes pour travailler ligne par ligne
    df_exploded = (
        df_jocas
        .reset_index(names="row_id")   # garder un identifiant pour reconstruire les listes
        .explode(col_jocas)             # crée une ligne par élément de la liste
    )

    # Nettoyer le DataFrame de correspondance
    df_comp_cat_clean = df_comp_cat.sort_values(
        by=col_cat, 
        key=lambda col: col.isna()    # met les NaN à la fin pour les ignorer
    ).drop_duplicates(subset=col_comp_cat, keep='first')  # garder une seule ligne par 'entrée'

    # Merge pour associer chaque élément à sa catégorie
    df_merged = df_exploded.merge(
        df_comp_cat_clean[[col_comp_cat, col_cat]],
        left_on=col_jocas,
        right_on=col_comp_cat,
        how="left"
    )

    # Remplacer les NaN résultants par None
    df_merged.loc[df_merged[col_cat].isna(), col_cat] = None

    # Regrouper les catégories par ligne originale
    cats_grouped = df_merged.groupby("row_id")[col_cat].apply(list)

    # Ajouter la nouvelle colonne dans df_jocas
    df_jocas[new_col_name] = df_jocas.index.map(cats_grouped)

    # S'assurer que les valeurs None sont correctement encodées comme listes
    df_jocas[col_jocas] = df_jocas[col_jocas].apply(
        lambda x: [None] if (x is None or (not isinstance(x, list) and x is None)) else x
    )

    return df_jocas


def test_column(df_jocas, col1='entree_cleanee_NER', col2='num_cat'):
    count = 0
    for _, row in df_jocas.iterrows():
        col1_values = row[col1]
        col2_values = row[col2]

        if (col1_values is not None and col2_values is None) or (col1_values is None and col2_values is not None):
            count += 1
            print(f"None mismatch : {col1_values} | {col2_values}")
        elif col1_values is not None and col2_values is not None and len(col1_values) != len(col2_values):
            count += 1
            print(f"Length mismatch {len(col1_values)} vs {len(col2_values)} : {col1_values} | {col2_values}")

    print(f"Number of mismatches : {count}")
