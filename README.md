# JobLess — Job Offer Breakdown with LLM Extraction & Skills Sorting

> **Mise en production d'un projet de Data Science** — INSEE / SSP Cloud

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live-blue?logo=github)](https://anhlinhpiketty.github.io/Mise_en_production_DS/)
[![Application](https://img.shields.io/badge/App-jobless--website.lab.sspcloud.fr-green)](https://jobless-website.lab.sspcloud.fr/)
[![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Présentation

**JobLess** est un outil d'analyse automatique d'offres d'emploi. À partir du texte brut d'une offre, il extrait les compétences mentionnées et les classe selon une taxonomie à plusieurs niveaux conçue à l'INSEE — distinguant compétences numériques, soft skills, domaines sectoriels, certifications, etc.

La pipeline combine un modèle NER fine-tuné (CamemBERTa-v2 via spaCy) pour l'extraction et des LLMs pour la classification, le tout exposé via une API FastAPI et une interface Streamlit.

---

## Fonctionnement

```
Texte d'offre d'emploi
        │
        ▼
┌───────────────────┐
│  Extraction NER   │  CamemBERTa-v2 (spaCy) — identifie les entités "compétence"
└───────────────────┘
        │  liste de compétences brutes
        ▼
┌───────────────────────────────────────────────────────────────────┐
│                    Pipeline de classification LLM                 │
│                                                                   │
│  Niveau 1 — Type : Soft Skill / Numérique / Non-numérique /      │
│             Domaine-Secteur / Certification                       │
│                                                                   │
│  Si "Numérique" :                                                 │
│    Niveau 2 — Thématique : Données & IA / Dev applicatif /       │
│               Infrastructure / Bureautique / …                   │
│    Niveau 3 — Niveau : Basique / Intermédiaire / Avancé          │
│    Niveau 4 — Catégorie IA : Machine Learning / IA générative … │
└───────────────────────────────────────────────────────────────────┘
        │
        ▼
  Résultats structurés (JSON)
```

Un **cache DuckDB** (alimenté par l'historique JOCAS 2019–2025) évite de rappeler les LLMs pour des compétences déjà classifiées.

---

## Structure du dépôt

```
Mise_en_production_DS/
├── .github/
│   └── workflows/
│       ├── deploy_pages.yml   # Build & déploiement GitHub Pages (Quarto)
│       ├── docker_back.yml    # Build & push image Docker backend
│       └── docker_front.yml   # Build & push image Docker frontend
│
├── app/
│   ├── api.py                 # API FastAPI (endpoint /analyze)
│   ├── Dockerfile             # Image Docker du backend
│   └── run.sh                 # Script de démarrage uvicorn
│
├── frontend/
│   ├── app.py                 # Interface Streamlit
│   └── Dockerfile             # Image Docker du frontend
│
├── src/
│   ├── classification.py      # Pipeline de classification LLM (4 niveaux)
│   ├── extraction.py          # Extraction NER via spaCy
│   ├── llm.py                 # Client LLM (API compatible OpenAI)
│   └── logging_config.py      # Configuration du logging
│
├── notebooks/
│   ├── test.ipynb             # Tests et expérimentations NER
│   └── test_classification.ipynb  # Tests de la classification
│
├── website/                   # Site de documentation (Quarto → GitHub Pages)
│   ├── index.qmd
│   ├── about.qmd
│   ├── _quarto.yml
│   └── styles.css
│
├── pyproject.toml             # Dépendances (gérées avec uv)
├── install.sh                 # Script d'installation locale
└── LICENSE                    # MIT
```

---

## Installation locale

### Prérequis

- Python 3.13
- [`uv`](https://github.com/astral-sh/uv)

### Étapes

```bash
# Cloner le dépôt
git clone https://github.com/anhlinhpiketty/Mise_en_production_DS.git
cd Mise_en_production_DS

# Installer les dépendances
./install.sh
# ou manuellement :
uv sync
```

### Variables d'environnement

Créez un fichier `.env` à la racine :

```env
API_KEY=votre_clé_api_llm
BASE_URL=https://llm.lab.sspcloud.fr/api
MODEL_NAME=gpt-oss:120b
S3_PATH=s3://votre-bucket/chemin
AWS_S3_ENDPOINT=minio.lab.sspcloud.fr
TEMPERATURE=0.0
```

---

## Lancer l'application

### Backend (API FastAPI)

```bash
uv run uvicorn app.api:app --reload
```

L'API est disponible sur `http://localhost:8000`. Documentation interactive : `http://localhost:8000/docs`.

**Endpoint principal :**

```
GET /analyze?desc_offre=<texte de l'offre>
```

Retourne une liste de compétences classifiées au format JSON.

### Frontend (Streamlit)

```bash
uv run streamlit run frontend/app.py
```

Interface disponible sur `http://localhost:8501`.

---

## Docker

### Backend

```bash
docker build \
  --build-arg BASE_URL=$BASE_URL \
  --build-arg MODEL_NAME=$MODEL_NAME \
  --build-arg S3_PATH=$S3_PATH \
  --build-arg AWS_S3_ENDPOINT=$AWS_S3_ENDPOINT \
  -f app/Dockerfile -t jobless-back .

docker run -e API_KEY=$API_KEY -p 8000:8000 jobless-back
```

### Frontend

```bash
docker build -f frontend/Dockerfile -t jobless-front .
docker run -p 8501:8501 jobless-front
```

---

## CI/CD

Trois workflows GitHub Actions sont configurés :

| Workflow | Déclencheur | Action |
|---|---|---|
| `deploy_pages.yml` | Push sur `main` | Build Quarto + déploiement GitHub Pages |
| `docker_back.yml` | Push sur `main`, branches actives, tags `v*` | Build & push image Docker backend sur Docker Hub |
| `docker_front.yml` | Push sur `main`, branches actives, tags `v*` | Build & push image Docker frontend sur Docker Hub |

### Secrets GitHub requis

| Secret | Description |
|---|---|
| `DOCKERHUB_USERNAME_BACK` | Nom d'utilisateur Docker Hub |
| `DOCKERHUB_TOKEN_BACK` | Token Docker Hub |

### Variables GitHub requises

| Variable | Description | Exemple |
|---|---|---|
| `BASE_URL` | URL de base de l'API LLM | `https://llm.lab.sspcloud.fr/api` |
| `MODEL_NAME` | Nom du modèle LLM | `gpt-oss:120b` |
| `S3_PATH` | Chemin du bucket S3 | `s3://bucket/diffusion/jobless` |
| `AWS_S3_ENDPOINT` | Endpoint MinIO | `minio.lab.sspcloud.fr` |

### Secret Kubernetes (déploiement SSP Cloud)

```bash
kubectl create secret generic api-jeton --from-literal=API_KEY='votre_clé_api_llm'
```

---

## Déploiement sur SSP Cloud

L'application est déployée sur **SSP Cloud** :

- L'API FastAPI tourne dans un conteneur Docker dédié
- Le frontend Streamlit tourne dans un conteneur séparé
- Les images sont publiées sur Docker Hub via GitHub Actions à chaque push

---

## Technologies

| Composant | Technologie |
|---|---|
| Extraction NER | [spaCy](https://spacy.io/) + CamemBERTa-v2 |
| Classification | LLM via API compatible OpenAI |
| Cache compétences | [DuckDB](https://duckdb.org/) |
| Stockage modèle/données | S3 (MinIO / SSP Cloud) |
| API | [FastAPI](https://fastapi.tiangolo.com/) + [uvicorn](https://www.uvicorn.org/) |
| Interface | [Streamlit](https://streamlit.io/) |
| Gestion dépendances | [uv](https://github.com/astral-sh/uv) |
| CI/CD | GitHub Actions |
| Documentation | [Quarto](https://quarto.org/) → GitHub Pages |

---

## Équipe

| Membre | Rôle |
|---|---|
| **Colas** | LLM & classification |
| **Arthur** | DevOps & déploiement |
| **Mateo** | DevOps & déploiement |
| **Anh Linh** | Frontend & GitHub Pages |

---

## Ressources

- [Application en ligne](https://jobless-website.lab.sspcloud.fr/)
- [Site de documentation](https://anhlinhpiketty.github.io/Mise_en_production_DS/)
- [Offres Data Scientist — France Travail](https://candidat.francetravail.fr/offres/emploi/data-scientist/s28m15)
- [Free-LLM (O-LLM)](https://github.com/O-LLM/Free-LLM)

---

## Licence

Ce projet est distribué sous licence [MIT](LICENSE).
