# pip install spacy dask[complete] ipywidgets spacy[transformers] datasets cupy-cuda12x
# nohup python -u spacy_infer.py > execution.log 2>&1 &
import spacy
import os
import torch
import s3fs
from tqdm import tqdm
import pandas as pd
import gc
import math
# ==========================================
# ⚙️ CONFIGURATION
# ==========================================

S3_ENDPOINT_URL = "https://" + os.environ["AWS_S3_ENDPOINT"]


fs = s3fs.S3FileSystem(
    endpoint_url=S3_ENDPOINT_URL,
    key="jocas-prod",
    secret="",
)

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
# Tes chemins S3 (sans s3:// pour s3fs, avec pour Ray)
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
SOURCE_PREFIX = "JOCAS_V3_NO_DUP_NO_PARTNER_NO_JIT"
DEST_PREFIX = "JOCAS_WITH_SKILLS"
CHUNK_SIZE = 20000

if not os.path.exists(LOCAL_MODEL_PATH):
    print("📥 Téléchargement du modèle...")
    fs.get(S3_MODEL_PATH, LOCAL_MODEL_PATH, recursive=True)
    print("✅ Téléchargement terminé.")
else:
    print("⚡ Modèle déjà présent localement, on passe le téléchargement.")

# 1. Config GPU
spacy.require_gpu()
nlp = spacy.load(LOCAL_MODEL_PATH)

# 3. Lister tous les fichiers Parquet source de manière récursive
print(f"🔍 Scan des fichiers dans {SOURCE_PATH}")
# glob permet de trouver tous les .parquet même dans les sous-dossiers
all_files = fs.glob(SOURCE_PATH)
print(all_files)
print(f"📦 Trouvé {len(all_files)} fichiers à traiter.")

# ==========================================
# 🔥 LA BOUCLE DE TRAITEMENT
# ==========================================

# On utilise tqdm pour suivre la progression fichier par fichier
for file_path in tqdm(all_files, unit="file"):
    # A. Calcul du chemin de destination (Miroir)
    # On remplace 'SOURCE_PREFIX' par 'DEST_PREFIX' dans le chemin
    # Ex: bucket/src/year=2024/file.parquet -> bucket/dest/year=2024/file.parquet
    dest_path = file_path.replace(SOURCE_PREFIX, DEST_PREFIX)

    # Si le fichier existe déjà, on skip (utile pour relancer après un crash)
    if fs.exists(dest_path):
        print(f"le fichier {dest_path} existe déjà")
        continue

    try:
        # B. Lecture du fichier (Pandas gère S3 via s3fs implicitement)
        # On lit directement depuis S3
        with fs.open(f"s3://{file_path}", "rb") as f:
            df = pd.read_parquet(f)
            len_df = len(df)
            print(f"fichier {dest_path} en cours de traitement : {len_df} lignes")

        # C. Inférence GPU (Batchée)
        # On extrait les entités
        df_skill_list = []

        num_chunks = math.ceil(len_df / CHUNK_SIZE)
        for i in range(0, len_df, CHUNK_SIZE):
            chunk_end = min(i + CHUNK_SIZE, len_df)
            chunk_idx = i // CHUNK_SIZE + 1
            if num_chunks > 1:
                print(
                    f"  👉 Chunk {chunk_idx}/{num_chunks} (Lignes {i} à {chunk_end})..."
                )

            texts = (
                df["description_full"]
                .iloc[i:chunk_end]  # by chunk
                .fillna("")
                .apply(lambda x: x[:5000])
                .astype(str)
            )

            chunk_skill_list = []
            # On utilise torch.amp pour la vitesse H100
            with torch.amp.autocast(device_type="cuda", dtype=torch.bfloat16):
                # On désactive les pipes inutiles
                with nlp.select_pipes(enable=["transformer", "ner"]):
                    nlp_list = nlp.pipe(texts, batch_size=1000)
                    for doc in nlp_list:
                        # Extraction légère (juste des strings)
                        ents = [e.text for e in doc.ents]
                        chunk_skill_list.append(str(ents))
            df_skill_list.extend(chunk_skill_list)
            del texts, chunk_skill_list
            gc.collect()
            torch.cuda.empty_cache()

        # Ajout de la colonne
        df["competences"] = df_skill_list

        # E. Écriture dans la destination (en conservant le partitionnement implicite)
        with fs.open(f"s3://{dest_path}", "wb") as f:
            df.to_parquet(f, index=False)
            print(f"fichier {dest_path} sauvegardé !")
        del doc, df  # Supprime les variables Python
        gc.collect()  # Nettoie la RAM CPU
        torch.cuda.empty_cache()  # Vide le cache VRAM GPU (Indispensable)
    except Exception as e:
        print(f"❌ Erreur sur {file_path}: {e}")
        # On continue quand même pour traiter les autres fichiers

print("✅ Terminé ! La nouvelle base est prête.")
