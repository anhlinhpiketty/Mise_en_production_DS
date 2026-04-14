# Mise_en_production_DS

## Idées :

 - Faire une API à qui on envoie une description d'offre d'emploi et qui retourne une liste de compétences avec des catégories qu'on a conçu à l'INSEE (genre numérique, soft skill et dans numérique ia, data, infra,...)
 - Rajouter un petit front pour utiliser l'API en mode user-friendly


## En pratique on a :

- Un modèle NER basé sur CamemBERTa-v2 entrainé via Spacy à extraire des compétences sur un corpus de descriptions d'offres annoté et augmenté par LLMs
- Normalisation de la formulation des compétences avec un LLM 
- 1ere classification LLM : Soft Skill, Compétence non numérique, Compétence numérique, Domaine / Secteur, Certification / Formation
- **Si compétence numérique** :
    - 2e classification LLM : Différentes thématiques du numérique (Bureautique et compétences générales; Développement applicatif; Données, Analytics & IA; Infrastructure, Systèmes & Réseaux; etc... )
    - 3e classification LLM : Différents niveaux de compétences numériques (Basique, Intermédiaire, Avancé)
    - 4e classification LLM : Différentes catégories de compétences IA (Machine Learning, IA générative, etc...)

Actuellement les prompts sont fait pour des batchs de plusieurs compétences.
Les LLMs utilisés étaient ceux du SSPCloud.

**Optionnel :** Comme un certains nombre de compétences ont déjà été classifiées ont pourra aussi faire un système pour stocker les compétences déjà classifiées pour éviter de devoir faire de nouveau appel aux LLM si on les trouve de nouveau dans une offre.


## Code :

Pour l'instant un peu un fourre-tout mais peut servir de base.

Personnelement (Colas), j'ai travaillé sur la partie classification LLM donc il me manque quelques trucs pour le modèle NER, je peux le récup mais j'ai pas toutes les données ainsi que les codes complets de traitement des données et d'entrainement --> Il faut que je demande à mon collègue.

Quelques indications :
- llm_augment_data.py --> Script pour générer des données supplémentaires pour l'entrainement du modèle NER
- train_spacy.py --> Une partie du script pour entrainer le modèle NER Spacy
- spacy_infer.py --> inférence du modèle NER sur Jocas (extraction de la compéte)
- skill_normalizer.py --> du code qui normalise les compétences extraites avec le modèle NER pour réduire le volume (pas forcement utile pour notre projet qui classifie on-the-fly)
- llm_infer.py --> script un peu standardisé de classification (utilisable avec différents prompts)
- setup_logging.py et utils.py --> différentes fonctions utilitaires pas toutes utiles pour notre projet

Dans /data --> quelques description annotées avec les compétences extraites mais sans les données augmentées

Dans /outputs --> un partie des compétences extraites de Jocas classifiées selon le type de compétences.

Dans /config_infer_llm --> un fichier de config exemple pour 


### Plan d'attaque

1. Entrainement du NER (MLFlow)
3. Classification LLM
4. Deploiement de l'API de la pipeline complète 
5. Déploiement d'une interface graphique


### Variables d'environement à renseigner :

#### **Secrets Kubernetes**
Créez un secret Kubernetes pour stocker la clé API LLM :
```bash
kubectl create secret generic api-jeton --from-literal=API_KEY='votre_clé_api_llm'
```
> **Note** : Remplacez `votre_clé_api_llm` par la clé API réelle fournie par votre service LLM.
---


#### **Variables GitHub**
Les variables suivantes doivent être définies dans les **paramètres de votre dépôt GitHub** (`Settings > Secrets and variables > Actions > Variables`) :

| Variable               | Description                                      | Exemple de valeur                          |
|------------------------|--------------------------------------------------|--------------------------------------------|
| `BASE_URL`             | URL de base de l'API LLM                         | `https://llm.lab.sspcloud.fr/api`          |
| `MODEL_NAME`           | Nom du modèle LLM à utiliser                     | `gpt-oss:120b`                             |
| `S3_PATH`              | Chemin du bucket S3 pour les données             | `s3://colaslepoutre/Classification_compétences_jocas` |
| `AWS_S3_ENDPOINT`      | Endpoint personnalisé pour le service S3 (MinIO)| `minio.lab.sspcloud.fr`                    |



### Free-LLM :

https://github.com/O-LLM/Free-LLM
