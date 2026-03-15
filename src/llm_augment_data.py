import os
import json
import re
import s3fs
import time
import logging  # <--- Ajout pour les logs
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm  # <--- Modification ici (plus de .notebook)
from openai import OpenAI

# --- CONFIGURATION DU LOGGING ---
# Cela va créer un fichier 'execution_ner.log' et afficher aussi dans la console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("execution_ner.log"),
        logging.StreamHandler()
    ]
)

S3_ENDPOINT_URL = "https://" + os.environ["AWS_S3_ENDPOINT"]

fs = s3fs.S3FileSystem(
    endpoint_url=S3_ENDPOINT_URL,
    key="jocas-prod",
    secret="",
)

BASE_URL = "https://llm.lab.sspcloud.fr/api"
API_KEY = ""
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

PROMPT = """

Ta mission est d'extraire UNIQUEMENT des concepts de compétences standardisés et précis.
Tu es un expert en extraction d'entités nommées (NER), plus particulièrement dans l'extraction de compétences depuis des données issues d'offres d'emploi en ligne.
Tu es également un expert en ontologie des compétences.
Tu vas recevoir en entrée une offre d'emploi, et ton objectif est d'en extraire les compétences en respectant strictement les règles suivantes.

# FORMAT DE SORTIE JSON :
# {"competences": [{"span": "texte exact extrait", "label": "SKILL"}]}

POINT D'ATTENTION CRITIQUE :
Chaque élément de la liste doit être une copie EXACTE (copier-coller) du texte présent dans l'offre.
Ne reformule pas, ne corrige pas les fautes, garde la casse originale.

DÉFINITIONS DES LABELS :

1. LABEL "SKILL" :
   - Ce sont des compétences ("élagage", "programmation informatique"); des outils ("Python", "Photoshop"), des spécialisations ("Data Science") ou des qualités ("autonomie", "sérieux")
   indispensables (ou appréciés) pour le poste.
   - Les SKILL doivent être mentionnés EXPLICITEMENT dans le corps de l'offre, et uniquement dans une section dédiée, souvent titrée "Profil", "compétences", "prérequis", "savoir-faire" etc.
   Parfois, la section ne comprend pas de tel titre, mais on trouve alors souvent une phrase type "Vous êtes : XXXX", "Vous maitrisez : XXXX". "vous devez savoir XXXX".
   - Tu ne dois donc JAMAIS labelliser comme SKILL un terme présent dans la partie "Missions" ou "tâches" de l'offre, ni dans la partie "description de l'entreprise".
   - Lorsqu'une formation ou une expérience sont évoqués, on extrait uniquement la spécialisation si elle est mentionnée ("bac +5 en génie civil" -> "génie civil")

2. LABEL "SKILL_EXTENDED" :
   - Ce label sert uniquement à extraire des compétences qui ne rentrent pas dans les critères du label "SKILL".
   - Utiliser ce label UNIQUEMENT sur des offres dont la description est très succinte et ne comprend pas de partie "profil" ou "compétences".
   - Il s'agit donc d'extraire des compétences mentionnées dans la partie "Missions" ou "tâches" de l'offre.
   - Attention à ne jamais extraire de termes de la partie "description de l'entreprise".
   - IMPORTANT : l'idée est d'extraire des compétences nécessaires pour le poste mais qui sont mentionnées en tant que taches au lieu d'être mentionnées dans une partie "profil".
   - TU NE DOIS EXTRAIRE AUCUNE TACHE A PART CELLES QUI DESIGNENT UNE COMPETENCE SPECIFIQUE OMISE DANS LA PARTIE PROFIL
   En particulier :
   - le terme doit se suffir à lui même : le terme isolé doit permettre à un recruteur de savoir de quel métier il s'agit ou quelle est la compétence technique précise.
   - On veut donc extraire une compétence formulée comme une mission ou une tâche, mais qui implique un savoir-faire technique SPECIFIQUE indispensable.
   - EXCLURE ainsi les tâches génériques ou floues (ex: "dialoguer avec les partenaires" -> NON, "piloter le projet phare de l'équipe" ->NON).
   - EXEMPLE positif : "élagage des arbres" dans une phrase comme "Recrute un spécialiste chargé de l'élagage des arbres" issue une description d'une offre très succinte.

RÈGLES D'EXTRACTION :
1. SPAN EXACT : Ne sélectionne que la compétence. Exclure "maîtrise de", "niveau expert en", "notions de".
   - "Maitrise de Python" -> Extraire "Python".
   - "SQL (avancé)" -> Extraire "SQL".
2. SPÉCIFICITÉ : Prends le terme le plus précis.
   - "Gestion de projet web" (Mieux que "Gestion de projet").
3. UNICITÉ : Pas de chevauchement.
   - "Python et Git" -> Extraire "Python", puis "Git".
4. EXCLUSIONS :
   - Ne pas extraire les TITRES de poste (ex: "On recherche un Data Scientist" -> RIEN).
   - EXCLURE ne rien annoter dans une phrase conjuguée au futur (ex: "vous gérerez des projets" -> NON, mais "gestion de projets" -> OUI).
5. EXACTITUDE : ne modifie JAMAIS une compétence : tu dois l'extraire telle quelle.

RÈGLES SPÉCIFIQUES PAR CATÉGORIE

1. COMPÉTENCES TECHNIQUES (HARD SKILLS) :
   - Lorsque la compétence implique la maitrise d'un logiciel ou d'un langage de programmation, extraire uniquement son nom
   -> Exemple :  "Programmation en langage C++" -> Extraire "C++".

2. SAVOIR-ÊTRE (SOFT SKILLS) et langues:
   - Repère notamment les termes exprimant un goût, une appétence ou une qualité personnelle.
   - Exemple 1:  "Vous avez un très bon sens de l'analyse" -> Extraire "sens de l'analyse".
   - Exemple 2:  "Une appétence pour les nouvelles technologies" -> Extraire "appétence pour les nouvelles technologies".
   - Exemple 3: "vous faites preuve de force de proposition" -> Extraire "force de proposition".
   - Repère toutes les mentions de langues : "un anglais technique est nécessaire pour ce poste" -> extraire "anglais"

3. DIPLÔMES ET FORMATIONS :
   - Règle générale : ne pas extraire de diplôme si la spécialité n'est pas mentionnée
   - Exemple : "titulaire d'un Bac+5" -> ne rien extraire
   - Si une spécialité est mentionnée, extraire uniquement celle-ci
   - Exemple : "Master en informatique" -> Extraire "informatique".
   - Exemple : "vous avez une formation en traitement du signal" -> "traitement du signal"
   - Extraire les noms de certifications comme "Qualibat"

EXEMPLES D'ANNOTATION :
Input: "  [...] Vous êtes Data Scientist et maitrisez Python. [...]"
Output: [{"span": "Python", "label": "SKILL"}] (On ignore le titre de poste Data Scientist)

Input: "  [...] Vous êtes issus d'une formation d'ingénieur avec un cursus en physique des matériaux"
Output: [{"span": "physique des matériaux", "label": "SKILL"}] (On extrait uniquement la spécialisation de la formation)

Input: "recrute un employé chargé de l'élagage des arbres à Paris."
Output: [{"span": "élagage des arbres", "label": "SKILL_EXTENDED"}] (la description est succinte, la tâche évoque expliciiement une compétence spécifique, technique,
dont la maitrise est absolument nécessaire et caractérise le métier)

Input: "Profil : autonome et minutieux."
Output: [{"span": "autonome", "label": "SKILL"}, {"span": "minutieux", "label": "SKILL"}] (on extrait les deux compétences séparémment)

Input: "En tant que manager, vous gérerez les conflits, piloterez les projets de l'équipe et assisterez à des réunions."
Output: [] (on extrait rien car on à affaire à une liste de tâches, non spécifiques, non formulées explicitement comme des compétences, comme en témoigne notamment les conjugaisons au futur)

Input: "vous devez être capable de concevoir une application orientée objet"
Output: [{"span": "concevoir une application orientée objet", "label": "SKILL"}] (c'est formulé explicitement formulé comme un prérequis pour le poste et pas simplement comme une tâche à effectuer)
"""

def clean_json_output(content):
    if "```" in content:
        match = re.search(r"```(?:json)?(.*?)```", content, re.DOTALL)
        if match:
            return match.group(1).strip()
    return content

def process_offer(offer_text, model_name, prompt):
    try:
        response = client.chat.completions.create(
            model=model_name,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": offer_text},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content
        clean_content = clean_json_output(content)
        return json.loads(clean_content)
    except Exception as e:
        return {"error": str(e), "text": offer_text[:50]}

# Attention : pd.read_csv n'accepte pas index=False en lecture, je l'ai retiré
try:
    df_train = pd.read_csv("sample_20K_train.csv", sep=";")
    logging.info(f"Chargement des données réussi : {len(df_train)} lignes.")
except Exception as e:
    logging.error(f"Erreur lors du chargement du CSV : {e}")
    raise e

def process_offer_safe(offer_text, model_name, prompt):
    try:
        return process_offer(offer_text, model_name, prompt)
    except Exception as e:
        logging.error(f"Erreur critique sur une offre : {e}")
        return {"competences": [], "error": str(e)}

def run_ner_campaign(all_offers, model_name, prompt, max_workers, batch_size):
    final_results = []
    
    logging.info(f"🚀 Démarrage de l'extraction sur {len(all_offers)} offres...")
    logging.info(f"⚡ Mode : {max_workers} threads parallèles")

    for i in range(0, len(all_offers), batch_size):
        batch_offers = all_offers[i : i + batch_size]
        logging.info(f"Traitement du lot {i} à {i + len(batch_offers)}...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # tqdm écrit maintenant sur stderr, ce qui est géré par nohup si besoin
            results_iterator = list(
                tqdm(
                    executor.map(
                        lambda x: process_offer_safe(x, model_name=model_name, prompt=prompt),
                        batch_offers,
                    ),
                    total=len(batch_offers),
                    desc=f"Batch {i//batch_size}"
                )
            )
            final_results.extend(results_iterator)

        # Sauvegarde intermédiaire
        with open("resultats_ner_raw_progress.json", "w", encoding="utf-8") as f:
            json.dump(final_results, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Batch {i//batch_size} terminé et sauvegardé.")
        time.sleep(1)

    return final_results


# --- CONFIGURATION ---
MAX_WORKERS = 10
BATCH_SIZE = 100
MODEL_NAME = "mistral-small3.2:24b"

if __name__ == "__main__":
    list_of_offers = df_train.description_full.to_list()

    full_results = run_ner_campaign(
        list_of_offers,
        model_name=MODEL_NAME,
        prompt=PROMPT,
        max_workers=MAX_WORKERS,
        batch_size=BATCH_SIZE,
    )

    logging.info(f"✅ Terminé ! {len(full_results)} résultats générés.")

    with open("resultats_ner_raw.json", "w", encoding="utf-8") as f:
        json.dump(full_results, f, ensure_ascii=False, indent=2)